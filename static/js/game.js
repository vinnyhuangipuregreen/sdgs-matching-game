// SDGs Matching Game Client Engine
const SoundEffects = {
  ctx: null,
  init() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();
    }
  },
  playTone(freq, type, duration, delay = 0) {
    try {
      this.init();
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime + delay);
      gain.gain.setValueAtTime(0.15, this.ctx.currentTime + delay);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + delay + duration);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(this.ctx.currentTime + delay);
      osc.stop(this.ctx.currentTime + delay + duration);
    } catch (e) {
      console.warn("Audio error:", e);
    }
  },
  correct() {
    this.playTone(523.25, "sine", 0.15, 0);     // C5
    this.playTone(659.25, "sine", 0.15, 0.1);   // E5
    this.playTone(783.99, "sine", 0.25, 0.2);   // G5
  },
  wrong() {
    this.playTone(220, "sawtooth", 0.2, 0);
    this.playTone(180, "sawtooth", 0.3, 0.15);
  },
  combo() {
    this.playTone(587.33, "triangle", 0.1, 0);
    this.playTone(880, "triangle", 0.25, 0.08);
  },
  victory() {
    [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => {
      this.playTone(f, "sine", 0.3, i * 0.12);
    });
  }
};

const GameApp = {
  state: {
    challenger: { nickname: "", organization: "", avatar: "🌱" },
    selectedMode: "standard",
    sessionId: null,
    questions: [],
    currentIndex: 0,
    score: 0,
    combo: 0,
    maxCombo: 0,
    correctCount: 0,
    totalQuestions: 10,
    startTime: null,
    timer: null,
    timePerQuestion: 20,
    timeRemaining: 20,
    isCardMode: false,
    cardFlipped: [],
    cardMatchedCount: 0,
    totalCardPairs: 0
  },

  init() {
    this.restoreChallengerProfile();
    this.bindEvents();
    this.loadGoalsReference();
  },

  restoreChallengerProfile() {
    const savedNickname = localStorage.getItem("sdgs_challenger_nickname");
    const savedOrg = localStorage.getItem("sdgs_challenger_org");
    const savedAvatar = localStorage.getItem("sdgs_challenger_avatar");
    if (savedNickname) {
      const el = document.getElementById("input-nickname");
      if (el) el.value = savedNickname;
      this.state.challenger.nickname = savedNickname;
    }
    if (savedOrg) {
      const el = document.getElementById("input-org");
      if (el) el.value = savedOrg;
      this.state.challenger.organization = savedOrg;
    }
    if (savedAvatar) {
      const el = document.getElementById("select-avatar");
      if (el) el.value = savedAvatar;
      this.state.challenger.avatar = savedAvatar;
    }
  },

  saveChallengerProfile(nickname, org, avatar) {
    if (nickname) localStorage.setItem("sdgs_challenger_nickname", nickname);
    if (org !== undefined) localStorage.setItem("sdgs_challenger_org", org);
    if (avatar) localStorage.setItem("sdgs_challenger_avatar", avatar);
  },

  bindEvents() {
    // Mode Selection
    document.querySelectorAll(".mode-card").forEach(card => {
      card.addEventListener("click", () => {
        document.querySelectorAll(".mode-card").forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        this.state.selectedMode = card.dataset.mode;
      });
    });

    // Start Button
    document.getElementById("btn-start-game").addEventListener("click", () => this.startGame());

    // Auto save profile on input change
    const nickEl = document.getElementById("input-nickname");
    const orgEl = document.getElementById("input-org");
    const avatarEl = document.getElementById("select-avatar");
    if (nickEl) nickEl.addEventListener("input", (e) => localStorage.setItem("sdgs_challenger_nickname", e.target.value.trim()));
    if (orgEl) orgEl.addEventListener("input", (e) => localStorage.setItem("sdgs_challenger_org", e.target.value.trim()));
    if (avatarEl) avatarEl.addEventListener("change", (e) => localStorage.setItem("sdgs_challenger_avatar", e.target.value));

    // Navigation buttons
    const btnNavModes = document.getElementById("btn-nav-modes");
    if (btnNavModes) btnNavModes.addEventListener("click", () => this.returnToLobby());

    const btnBackModes = document.getElementById("btn-back-modes");
    if (btnBackModes) btnBackModes.addEventListener("click", () => this.returnToLobby());

    document.getElementById("btn-nav-leaderboard").addEventListener("click", () => this.openLeaderboard());
    document.getElementById("btn-nav-handbook").addEventListener("click", () => this.openHandbook());
    document.getElementById("btn-modal-close").addEventListener("click", () => this.closeModal());
    document.getElementById("btn-restart-game").addEventListener("click", () => this.returnToLobby());
    document.getElementById("btn-view-rankings").addEventListener("click", () => {
      this.closeModal();
      this.openLeaderboard();
    });

    // Close modal on click outside
    document.getElementById("modal-overlay").addEventListener("click", (e) => {
      if (e.target.id === "modal-overlay") this.closeModal();
    });
  },

  async loadGoalsReference() {
    try {
      const res = await fetch("/api/game/goals");
      this.goals = await res.json();
    } catch (e) {
      console.error("Failed to load goals", e);
    }
  },

  async startGame() {
    const nicknameInput = document.getElementById("input-nickname").value.trim();
    if (!nicknameInput) {
      alert("請輸入挑戰者暱稱！");
      document.getElementById("input-nickname").focus();
      return;
    }

    this.state.challenger.nickname = nicknameInput;
    this.state.challenger.organization = document.getElementById("input-org").value.trim() || "一般挑戰者";
    this.state.challenger.avatar = document.getElementById("select-avatar").value || "🌱";
    this.saveChallengerProfile(this.state.challenger.nickname, this.state.challenger.organization, this.state.challenger.avatar);

    // Request start game session from API
    try {
      const res = await fetch("/api/game/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nickname: this.state.challenger.nickname,
          organization: this.state.challenger.organization,
          avatar: this.state.challenger.avatar,
          mode: this.state.selectedMode,
          question_count: 10
        })
      });
      const data = await res.json();
      this.state.sessionId = data.session_id;
      this.state.score = 0;
      this.state.combo = 0;
      this.state.maxCombo = 0;
      this.state.correctCount = 0;
      this.state.currentIndex = 0;
      this.state.startTime = Date.now();

      // Switch view
      document.getElementById("view-welcome").classList.remove("active");
      document.getElementById("view-gameplay").classList.add("active");

      // Update Header
      document.getElementById("display-challenger").innerText = `${this.state.challenger.avatar} ${this.state.challenger.nickname}`;
      this.updateScoreDisplay();

      if (this.state.selectedMode === "cards") {
        this.state.isCardMode = true;
        this.setupCardMode(data.questions.cards, data.questions.total_pairs);
      } else {
        this.state.isCardMode = false;
        this.state.questions = data.questions;
        this.state.totalQuestions = data.questions.length;
        document.getElementById("cards-board").style.display = "none";
        document.getElementById("standard-board").style.display = "block";
        this.renderQuestion();
      }
    } catch (e) {
      alert("遊戲啟動失敗，請確認後端服務運作正常。");
      console.error(e);
    }
  },

  updateScoreDisplay() {
    document.getElementById("display-score").innerText = this.state.score;
    const comboEl = document.getElementById("display-combo");
    if (this.state.combo >= 2) {
      comboEl.style.display = "inline-flex";
      comboEl.innerText = `🔥 ${this.state.combo} 連擊!`;
    } else {
      comboEl.style.display = "none";
    }
  },

  renderQuestion() {
    clearInterval(this.state.timer);
    const q = this.state.questions[this.state.currentIndex];
    if (!q) {
      this.finishGame();
      return;
    }

    // Progress
    document.getElementById("display-progress").innerText = `${this.state.currentIndex + 1} / ${this.state.totalQuestions}`;

    // Prompt
    const badgeEl = document.getElementById("question-badge");
    const textEl = document.getElementById("question-text");
    const extraEl = document.getElementById("question-extra");

    if (q.type === "scenario") {
      badgeEl.innerText = "生活情境指標";
      badgeEl.style.background = "#e0f2fe";
      badgeEl.style.color = "#0369a1";
      textEl.innerText = q.prompt_text;
      extraEl.style.display = "inline-block";
      extraEl.innerText = `💡 生活日常範例：${q.real_life_example}`;
    } else {
      badgeEl.innerText = `細項 ${q.code} · ${q.target_type}`;
      badgeEl.style.background = q.target_type.includes("執行方法") ? "#fef3c7" : "#dcfce7";
      badgeEl.style.color = q.target_type.includes("執行方法") ? "#92400e" : "#166534";
      textEl.innerText = q.prompt_text;
      extraEl.style.display = "none";
    }

    // Options Grid
    const optionsGrid = document.getElementById("options-grid");
    optionsGrid.innerHTML = "";

    q.options.forEach(opt => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.innerHTML = `
        <div class="opt-icon" style="background:${opt.color}; color:#fff; border-radius:8px; padding:6px;">${opt.icon || "🎯"}</div>
        <div class="opt-details">
          <h4 style="color:${opt.color}">${opt.code} ${opt.name}</h4>
          <p>點擊配對此目標</p>
        </div>
      `;
      btn.addEventListener("click", () => this.handleOptionClick(btn, opt.id, q));
      optionsGrid.appendChild(btn);
    });

    // Start Timer
    this.startQuestionTimer();
  },

  startQuestionTimer() {
    this.state.timeRemaining = this.state.timePerQuestion;
    const bar = document.getElementById("timer-bar");
    const num = document.getElementById("timer-seconds");

    bar.style.width = "100%";
    bar.style.backgroundColor = "#10b981";
    num.innerText = `${this.state.timeRemaining}s`;

    this.state.timer = setInterval(() => {
      this.state.timeRemaining--;
      const pct = (this.state.timeRemaining / this.state.timePerQuestion) * 100;
      bar.style.width = `${pct}%`;
      num.innerText = `${this.state.timeRemaining}s`;

      if (this.state.timeRemaining <= 5) {
        bar.style.backgroundColor = "#ef4444";
      } else if (this.state.timeRemaining <= 10) {
        bar.style.backgroundColor = "#f59e0b";
      }

      if (this.state.timeRemaining <= 0) {
        clearInterval(this.state.timer);
        this.handleTimeout();
      }
    }, 1000);
  },

  async handleOptionClick(btnEl, selectedGoalId, question) {
    clearInterval(this.state.timer);
    // Disable all options
    document.querySelectorAll(".option-btn").forEach(b => b.disabled = true);

    const timeSpent = (this.state.timePerQuestion - this.state.timeRemaining) * 1000;

    try {
      const res = await fetch("/api/game/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.state.sessionId,
          question_index: this.state.currentIndex,
          target_id: question.target_id,
          scenario_id: question.scenario_id,
          selected_goal_id: selectedGoalId,
          correct_goal_id: question.correct_goal_id,
          time_spent_ms: timeSpent,
          current_combo: this.state.combo
        })
      });
      const data = await res.json();

      if (data.is_correct) {
        btnEl.classList.add("correct");
        this.state.correctCount++;
        this.state.combo = data.new_combo;
        if (this.state.combo > this.state.maxCombo) {
          this.state.maxCombo = this.state.combo;
        }
        this.state.score += data.score_delta;
        if (this.state.combo >= 2) SoundEffects.combo();
        else SoundEffects.correct();
      } else {
        btnEl.classList.add("wrong");
        this.state.combo = 0;
        this.state.score = Math.max(0, this.state.score + data.score_delta);
        SoundEffects.wrong();

        // Highlight correct option
        document.querySelectorAll(".option-btn").forEach(b => {
          if (b.innerText.includes(data.correct_goal.code)) {
            b.classList.add("correct");
          }
        });
      }

      this.updateScoreDisplay();

      // Show brief feedback and next question
      setTimeout(() => {
        this.showExplanationModal(data);
      }, 700);

    } catch (e) {
      console.error(e);
      this.nextQuestion();
    }
  },

  handleTimeout() {
    SoundEffects.wrong();
    this.state.combo = 0;
    this.state.score = Math.max(0, this.state.score - 20);
    this.updateScoreDisplay();
    alert("時間到！很可惜錯過了配對機會。");
    this.nextQuestion();
  },

  showExplanationModal(answerData) {
    const modal = document.getElementById("modal-overlay");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    title.innerHTML = answerData.is_correct ? "🎉 配對成功！" : "❌ 配對錯誤";
    title.style.color = answerData.is_correct ? "#059669" : "#dc2626";

    const g = answerData.correct_goal;
    const t = answerData.target;

    body.innerHTML = `
      <div style="border-left: 5px solid ${g.color}; padding-left: 1rem; margin-bottom: 1rem;">
        <h3 style="color:${g.color}; margin-bottom: 0.25rem;">${g.code} ${g.name}</h3>
        <p style="font-size:0.9rem; color:#475569;"><strong>目標全文：</strong>${g.full_name}</p>
        <p style="font-size:0.85rem; color:#64748b; margin-top:0.25rem;">5P領域分類：<strong>${g.category_zh} (People/Planet/Prosperity/Peace/Partnership)</strong></p>
      </div>
      ${t ? `
      <div style="background:#f8fafc; border-radius:8px; padding:1rem; margin-bottom:1rem;">
        <span class="target-badge" style="background:#e2e8f0;">細項指標 ${t.code} · ${t.type}</span>
        <p style="font-size:0.95rem; margin-top:0.5rem; line-height:1.6;">${t.description}</p>
      </div>` : ''}
      <button class="btn btn-primary" id="btn-next-step" style="width:100%; margin-top:1rem;">前往下一題 ➔</button>
    `;

    document.getElementById("btn-next-step").onclick = () => {
      this.closeModal();
      this.nextQuestion();
    };

    modal.classList.add("open");
  },

  nextQuestion() {
    this.state.currentIndex++;
    if (this.state.currentIndex < this.state.totalQuestions) {
      this.renderQuestion();
    } else {
      this.finishGame();
    }
  },

  /* Card Flip Match Mode Implementation */
  setupCardMode(cards, totalPairs) {
    document.getElementById("standard-board").style.display = "none";
    const cardsBoard = document.getElementById("cards-board");
    cardsBoard.style.display = "grid";
    cardsBoard.innerHTML = "";

    this.state.cardFlipped = [];
    this.state.cardMatchedCount = 0;
    this.state.totalCardPairs = totalPairs;
    this.state.totalQuestions = totalPairs;

    document.getElementById("display-progress").innerText = `0 / ${totalPairs} 配對完成`;

    cards.forEach(card => {
      const cardEl = document.createElement("div");
      cardEl.className = "flip-card";
      cardEl.dataset.pairKey = card.pair_key;
      cardEl.dataset.cardId = card.card_id;
      cardEl.dataset.goalId = card.goal_id;

      cardEl.innerHTML = `
        <div class="flip-card-back">🌱</div>
        <div class="flip-card-content">
          <span style="font-size:0.75rem; font-weight:700; color:${card.color}; background:#f1f5f9; padding:2px 6px; border-radius:4px;">${card.badge}</span>
          <h4 style="font-size:0.95rem; margin:6px 0; color:${card.color};">${card.title}</h4>
          <p style="font-size:0.75rem; color:#475569; line-height:1.4;">${card.text}</p>
        </div>
      `;

      cardEl.addEventListener("click", () => this.handleCardFlip(cardEl));
      cardsBoard.appendChild(cardEl);
    });
  },

  handleCardFlip(cardEl) {
    if (cardEl.classList.contains("flipped") || cardEl.classList.contains("matched")) return;
    if (this.state.cardFlipped.length >= 2) return;

    cardEl.classList.add("flipped");
    this.state.cardFlipped.push(cardEl);

    if (this.state.cardFlipped.length === 2) {
      const [c1, c2] = this.state.cardFlipped;
      if (c1.dataset.pairKey === c2.dataset.pairKey) {
        // Matched
        setTimeout(() => {
          c1.classList.add("matched");
          c2.classList.add("matched");
          this.state.cardMatchedCount++;
          this.state.correctCount++;
          this.state.combo++;
          if (this.state.combo > this.state.maxCombo) this.state.maxCombo = this.state.combo;
          this.state.score += 150 + (this.state.combo - 1) * 30;
          this.updateScoreDisplay();
          SoundEffects.correct();
          this.state.cardFlipped = [];

          document.getElementById("display-progress").innerText = `${this.state.cardMatchedCount} / ${this.state.totalCardPairs} 配對完成`;

          if (this.state.cardMatchedCount === this.state.totalCardPairs) {
            setTimeout(() => this.finishGame(), 500);
          }
        }, 500);
      } else {
        // Not matched
        setTimeout(() => {
          c1.classList.remove("flipped");
          c2.classList.remove("flipped");
          this.state.combo = 0;
          this.state.score = Math.max(0, this.state.score - 15);
          this.updateScoreDisplay();
          SoundEffects.wrong();
          this.state.cardFlipped = [];
        }, 900);
      }
    }
  },

  async finishGame() {
    clearInterval(this.state.timer);
    SoundEffects.victory();
    const timeTaken = Math.round((Date.now() - this.state.startTime) / 1000);

    try {
      const res = await fetch("/api/game/finish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.state.sessionId,
          total_score: this.state.score,
          total_questions: this.state.totalQuestions,
          correct_count: this.state.correctCount,
          combo_max: this.state.maxCombo,
          time_taken_seconds: timeTaken
        })
      });
      const data = await res.json();
      this.showResultModal(data);
    } catch (e) {
      console.error("Failed to finish session", e);
      alert("遊戲結算時發生問題，但分數已記錄在前端。");
    }
  },

  showResultModal(result) {
    const modal = document.getElementById("modal-overlay");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    title.innerHTML = "🏆 挑戰結算證書 (Challenge Complete)";
    title.style.color = "#1e293b";

    body.innerHTML = `
      <div style="text-align:center; padding:1rem 0;">
        <div style="font-size:3.5rem; margin-bottom:0.5rem;">🎖️</div>
        <h2 style="color:#2563eb; font-size:1.6rem; margin-bottom:0.25rem;">${result.badge}</h2>
        <p style="color:#64748b; font-size:0.9rem;">挑戰者：<strong>${this.state.challenger.nickname}</strong> (${this.state.challenger.organization})</p>
        
        <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; margin:1.5rem 0; text-align:left;">
          <div style="background:#f8fafc; border-radius:8px; padding:1rem; border:1px solid #e2e8f0;">
            <div style="font-size:0.75rem; color:#64748b;">最終總得分</div>
            <div style="font-size:1.75rem; font-weight:700; color:#10b981;">${result.total_score} 分</div>
          </div>
          <div style="background:#f8fafc; border-radius:8px; padding:1rem; border:1px solid #e2e8f0;">
            <div style="font-size:0.75rem; color:#64748b;">即時全服排名</div>
            <div style="font-size:1.75rem; font-weight:700; color:#f59e0b;">第 ${result.rank} 名</div>
          </div>
          <div style="background:#f8fafc; border-radius:8px; padding:1rem; border:1px solid #e2e8f0;">
            <div style="font-size:0.75rem; color:#64748b;">配對正確率</div>
            <div style="font-size:1.75rem; font-weight:700; color:#3b82f6;">${result.accuracy_pct}%</div>
          </div>
          <div style="background:#f8fafc; border-radius:8px; padding:1rem; border:1px solid #e2e8f0;">
            <div style="font-size:0.75rem; color:#64748b;">最高連擊 / 耗時</div>
            <div style="font-size:1.2rem; font-weight:700; color:#64748b;">🔥 ${result.combo_max} 次 / ⏱️ ${result.time_taken}秒</div>
          </div>
        </div>

        <div style="display:flex; gap:0.75rem; justify-content:center; margin-top:1.5rem;">
          <button class="btn btn-secondary" onclick="GameApp.returnToLobby()">返回大廳</button>
          <button class="btn btn-primary" onclick="GameApp.openLeaderboard()">查看排行榜</button>
        </div>
      </div>
    `;

    modal.classList.add("open");
  },

  async openLeaderboard() {
    const modal = document.getElementById("modal-overlay");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    title.innerHTML = "🏆 SDGs 永續英雄排行榜 (Leaderboard)";
    title.style.color = "#1e293b";

    body.innerHTML = `<div style="text-align:center; padding:2rem;">載入中...</div>`;
    modal.classList.add("open");

    try {
      const res = await fetch("/api/game/leaderboard?limit=20");
      const list = await res.json();

      let rowsHtml = list.map((item, i) => {
        let rankBadge = `${i + 1}`;
        if (i === 0) rankBadge = "🥇 1";
        if (i === 1) rankBadge = "🥈 2";
        if (i === 2) rankBadge = "🥉 3";

        return `
          <tr>
            <td><strong>${rankBadge}</strong></td>
            <td>${item.avatar} <strong>${item.nickname}</strong></td>
            <td>${item.organization || "-"}</td>
            <td><span class="target-badge">${item.mode}</span></td>
            <td><strong style="color:#10b981;">${item.total_score}</strong></td>
            <td>${item.accuracy}%</td>
            <td>${item.time_taken_seconds}s</td>
          </tr>
        `;
      }).join("");

      body.innerHTML = `
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>名次</th>
                <th>挑戰者</th>
                <th>組織/學校</th>
                <th>模式</th>
                <th>總分</th>
                <th>正確率</th>
                <th>用時</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml || `<tr><td colspan="7" style="text-align:center; padding:1.5rem;">尚未有挑戰紀錄，快來搶下首勝！</td></tr>`}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      body.innerHTML = `<p style="color:red;">載入排行榜失敗。</p>`;
    }
  },

  async openHandbook() {
    const modal = document.getElementById("modal-overlay");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    title.innerHTML = "📖 SDGs 17項目標與169項細項學習手冊";
    body.innerHTML = `<div style="text-align:center; padding:2rem;">載入百科知識庫...</div>`;
    modal.classList.add("open");

    try {
      const res = await fetch("/api/game/goals");
      const goals = await res.json();

      let goalsHtml = goals.map(g => `
        <div style="border-left: 4px solid ${g.color}; background:#f8fafc; border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.75rem;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h4 style="color:${g.color}; font-size:1rem;">${g.code} ${g.name}</h4>
            <span style="font-size:0.75rem; background:#e2e8f0; padding:2px 6px; border-radius:4px;">${g.category_zh}領域</span>
          </div>
          <p style="font-size:0.85rem; color:#334155; margin-top:4px;">${g.full_name}</p>
          ${g.slogan ? `<p style="font-size:0.8rem; color:#64748b; margin-top:2px;"><em>💡 ${g.slogan} (${g.example})</em></p>` : ''}
        </div>
      `).join("");

      body.innerHTML = `
        <p style="font-size:0.85rem; color:#64748b; margin-bottom:1rem;">
          聯合國 2030 永續發展目標包含 17 項核心目標與 169 項具體細項目標，核心精神為「不遺漏任何人」。
        </p>
        <div style="max-height:60vh; overflow-y:auto;">
          ${goalsHtml}
        </div>
      `;
    } catch (e) {
      body.innerHTML = `<p style="color:red;">載入資料庫失敗。</p>`;
    }
  },

  returnToLobby() {
    this.closeModal();
    clearInterval(this.state.timer);
    document.getElementById("view-gameplay").classList.remove("active");
    document.getElementById("view-welcome").classList.add("active");
  },

  closeModal() {
    document.getElementById("modal-overlay").classList.remove("open");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  GameApp.init();
});
