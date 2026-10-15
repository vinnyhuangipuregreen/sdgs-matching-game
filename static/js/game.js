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
    answerPending: false,
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
    this.state.answerPending = false;
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
    if (this.state.answerPending) return;
    this.state.answerPending = true;
    const sessionId = this.state.sessionId;
    const questionIndex = this.state.currentIndex;
    const isCurrentQuestion = () => this.state.sessionId === sessionId
      && this.state.currentIndex === questionIndex
      && document.getElementById("view-gameplay").classList.contains("active");
    clearInterval(this.state.timer);
    // Disable all options
    document.querySelectorAll(".option-btn").forEach(b => b.disabled = true);
    btnEl.classList.add("pending");
    btnEl.setAttribute("aria-busy", "true");
    const label = btnEl.querySelector(".opt-details p");
    label.textContent = "已選擇，正在判定…";

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
      if (!res.ok) throw new Error(`Answer request failed: ${res.status}`);
      const data = await res.json();
      if (!isCurrentQuestion()) return;
      btnEl.classList.remove("pending");
      btnEl.removeAttribute("aria-busy");
      label.textContent = data.is_correct ? "配對成功！" : "配對錯誤";

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
        if (isCurrentQuestion()) this.showExplanationModal(data);
      }, 250);

    } catch (e) {
      console.error(e);
      if (isCurrentQuestion()) this.nextQuestion();
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

  MODE_NAMES: {
    scenario: "生活情境入門",
    standard: "標準細項配對",
    cards: "翻牌記憶連連看",
    master169: "169細項極限闖關"
  },

  MODE_ICONS: {
    scenario: "🏡",
    standard: "🎯",
    cards: "🃏",
    master169: "👑"
  },

  MODE_DESCRIPTIONS: {
    scenario: "日常生活具體案例與 17 目標直覺配對（例：惜食、節電、淨灘）",
    standard: "隨機抽取 169 細項具體承諾，精準判斷所屬 17 大核心目標",
    cards: "經典 16 卡牌翻牌短時記憶，目標卡與細項卡兩兩連線配對",
    master169: "30 題極限連續高壓測驗，考驗對成果目標與執行方法的透徹度"
  },

  openLeaderboard(initialMode) {
    const modal = document.getElementById("modal-overlay");
    const modalCard = modal.querySelector(".modal-card");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    modalCard.className = "modal-card modal-leaderboard";
    title.innerHTML = "🏆 SDGs 永續英雄排行榜 (Leaderboard)";
    title.style.color = "#1e293b";

    const activeMode = initialMode || this.state.selectedMode || "scenario";

    body.innerHTML = `
      <!-- 4 大模式切換頁籤 -->
      <div class="leaderboard-tabs">
        <button class="leaderboard-tab-btn ${activeMode === 'scenario' ? 'active' : ''}" data-mode="scenario" onclick="GameApp.switchLeaderboardTab('scenario')">
          🏡 生活情境入門
        </button>
        <button class="leaderboard-tab-btn ${activeMode === 'standard' ? 'active' : ''}" data-mode="standard" onclick="GameApp.switchLeaderboardTab('standard')">
          🎯 標準細項配對
        </button>
        <button class="leaderboard-tab-btn ${activeMode === 'cards' ? 'active' : ''}" data-mode="cards" onclick="GameApp.switchLeaderboardTab('cards')">
          🃏 翻牌記憶連連看
        </button>
        <button class="leaderboard-tab-btn ${activeMode === 'master169' ? 'active' : ''}" data-mode="master169" onclick="GameApp.switchLeaderboardTab('master169')">
          👑 169細項極限闖關
        </button>
      </div>

      <!-- 模式介紹提示 -->
      <div id="leaderboard-mode-desc" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:0.5rem; padding:0.6rem 1rem; margin-bottom:1rem; font-size:0.83rem; color:#475569; display:flex; align-items:center; gap:0.5rem;">
        <span>${this.MODE_ICONS[activeMode]}</span>
        <span><strong>${this.MODE_NAMES[activeMode]} 排行榜：</strong>${this.MODE_DESCRIPTIONS[activeMode]}</span>
      </div>

      <!-- 列表內容區域 -->
      <div id="leaderboard-tab-content" style="min-height:240px;">
        <div style="text-align:center; padding:3rem; color:#64748b;">
          <div style="font-size:2rem; animation:pulse 1s infinite;">🌱</div>
          <p style="margin-top:0.5rem;">正在讀取 ${this.MODE_NAMES[activeMode]} 排行榜...</p>
        </div>
      </div>
    `;

    modal.classList.add("open");
    this.loadLeaderboardData(activeMode);
  },

  switchLeaderboardTab(mode) {
    document.querySelectorAll(".leaderboard-tab-btn").forEach(btn => {
      if (btn.dataset.mode === mode) btn.classList.add("active");
      else btn.classList.remove("active");
    });

    const descEl = document.getElementById("leaderboard-mode-desc");
    if (descEl) {
      descEl.innerHTML = `
        <span>${this.MODE_ICONS[mode]}</span>
        <span><strong>${this.MODE_NAMES[mode]} 排行榜：</strong>${this.MODE_DESCRIPTIONS[mode]}</span>
      `;
    }

    const contentEl = document.getElementById("leaderboard-tab-content");
    if (contentEl) {
      contentEl.innerHTML = `
        <div style="text-align:center; padding:3rem; color:#64748b;">
          <div style="font-size:2rem; animation:pulse 1s infinite;">🌱</div>
          <p style="margin-top:0.5rem;">正在讀取 ${this.MODE_NAMES[mode]} 排行榜...</p>
        </div>
      `;
    }

    this.loadLeaderboardData(mode);
  },

  async loadLeaderboardData(mode) {
    const contentEl = document.getElementById("leaderboard-tab-content");
    if (!contentEl) return;

    try {
      const res = await fetch(`/api/game/leaderboard?mode=${mode}&limit=30`);
      const list = await res.json();

      if (!list || list.length === 0) {
        contentEl.innerHTML = `
          <div style="text-align:center; padding:3rem 1rem; color:#64748b; background:#f8fafc; border-radius:0.75rem; border:1px dashed #cbd5e1; margin-top:0.5rem;">
            <div style="font-size:2.8rem; margin-bottom:0.5rem;">${this.MODE_ICONS[mode]}</div>
            <h4 style="color:#1e293b; font-size:1.1rem; margin-bottom:0.35rem;">目前「${this.MODE_NAMES[mode]}」模式尚無挑戰紀錄</h4>
            <p style="font-size:0.85rem; color:#64748b; max-width:400px; margin:0 auto 1.25rem auto;">
              還沒有挑戰者登上這個排行榜，現在就是搶下全服第一名的最佳時機！
            </p>
            <button class="btn btn-primary" style="padding:0.6rem 1.75rem; border-radius:9999px; font-size:0.9rem;" onclick="GameApp.selectModeAndStart('${mode}')">
              🚀 立即挑戰「${this.MODE_NAMES[mode]}」
            </button>
          </div>
        `;
        return;
      }

      let rowsHtml = list.map((item, i) => {
        let rankBadge = `${i + 1}`;
        if (i === 0) rankBadge = "🥇 1";
        if (i === 1) rankBadge = "🥈 2";
        if (i === 2) rankBadge = "🥉 3";

        const modeZh = this.MODE_NAMES[item.mode] || item.mode;

        return `
          <tr>
            <td style="font-size:1rem;"><strong>${rankBadge}</strong></td>
            <td>
              <div style="display:flex; align-items:center; gap:0.4rem;">
                <span style="font-size:1.2rem;">${item.avatar}</span>
                <strong style="color:#1e293b;">${item.nickname}</strong>
              </div>
            </td>
            <td style="color:#475569;">${item.organization || "-"}</td>
            <td><span class="badge-mode-zh mode-${item.mode}">${modeZh}</span></td>
            <td><strong style="color:#10b981; font-size:1.05rem;">${item.total_score}</strong> 分</td>
            <td style="font-weight:600; color:#2563eb;">${item.accuracy}%</td>
            <td><span style="color:#d97706; font-weight:700;">🔥 ${item.combo_max}</span></td>
            <td style="color:#64748b;">${item.time_taken_seconds} 秒</td>
            <td style="font-size:0.78rem; color:#94a3b8;">${item.completed_at ? item.completed_at.slice(0, 16) : '-'}</td>
          </tr>
        `;
      }).join("");

      contentEl.innerHTML = `
        <div class="table-container" style="max-height:55vh; overflow-y:auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:70px;">名次</th>
                <th>挑戰者</th>
                <th>所屬組織</th>
                <th>模式</th>
                <th>總得分</th>
                <th>正確率</th>
                <th>最高連擊</th>
                <th>耗時</th>
                <th>完成時間</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      console.error(e);
      contentEl.innerHTML = `<p style="color:red; text-align:center; padding:2rem;">載入排行榜失敗，請確認網路與服務正常。</p>`;
    }
  },

  selectModeAndStart(mode) {
    this.closeModal();
    this.returnToLobby();
    const targetCard = document.querySelector(`.mode-card[data-mode="${mode}"]`);
    if (targetCard) {
      document.querySelectorAll(".mode-card").forEach(c => c.classList.remove("selected"));
      targetCard.classList.add("selected");
      this.state.selectedMode = mode;
      targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const nickEl = document.getElementById("input-nickname");
    if (nickEl && !nickEl.value.trim()) {
      nickEl.focus();
    }
  },

  async openHandbook() {
    const modal = document.getElementById("modal-overlay");
    const modalCard = modal.querySelector(".modal-card");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    modalCard.classList.add("modal-handbook");
    title.innerHTML = "📖 SDGs 17項目標 × 169項細項目標 官方學習手冊";
    title.style.color = "#1e3a8a";

    body.innerHTML = `<div style="text-align:center; padding:3rem;"><div style="font-size:2rem; animation:pulse 1s infinite;">🌱</div><p style="margin-top:0.5rem; color:#64748b;">正在載入 17 項目標與 169 項細項完整知識庫...</p></div>`;
    modal.classList.add("open");

    try {
      const res = await fetch("/api/game/handbook");
      const data = await res.json();
      this.handbookData = data;
      this.renderHandbookContent(data);
    } catch (e) {
      console.error(e);
      body.innerHTML = `<p style="color:red; text-align:center; padding:2rem;">載入失敗，請確認後端服務正常運作。</p>`;
    }
  },

  renderHandbookContent(data, filterCategory = "all", searchQuery = "") {
    const body = document.getElementById("modal-body");
    const goals = data.goals;

    // Quick navigation badges (1-17)
    const quickNavHtml = goals.map(g => `
      <button class="quick-sdg-btn" style="background:${g.color};" onclick="GameApp.scrollToGoal(${g.id})" title="SDG ${g.id} ${g.name}">
        ${g.id}
      </button>
    `).join("");

    // Filter goals
    let filteredGoals = goals;
    if (filterCategory !== "all") {
      filteredGoals = filteredGoals.filter(g => g.category.toLowerCase() === filterCategory.toLowerCase() || g.category_zh === filterCategory);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase().trim();
      filteredGoals = filteredGoals.filter(g => {
        const inGoal = g.name.toLowerCase().includes(q) || g.full_name.toLowerCase().includes(q) || (g.slogan && g.slogan.toLowerCase().includes(q));
        const inOutcomes = g.outcome_targets.some(t => t.code.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
        const inMeans = g.means_targets.some(t => t.code.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
        return inGoal || inOutcomes || inMeans;
      });
    }

    const goalsHtml = filteredGoals.map(g => {
      // Filter targets if search active
      let outcomes = g.outcome_targets;
      let means = g.means_targets;
      if (searchQuery) {
        const q = searchQuery.toLowerCase().trim();
        outcomes = outcomes.filter(t => t.code.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
        means = means.filter(t => t.code.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
      }

      const outcomeItemsHtml = outcomes.map(t => `
        <div class="handbook-target-card">
          <div class="target-num-badge" style="background:${g.color};">${t.code}</div>
          <div class="target-content">
            <span class="target-tag-outcome">成果目標 (要達成什麼)</span>
            <div class="target-desc-text">${t.description}</div>
          </div>
        </div>
      `).join("");

      const meansItemsHtml = means.map(t => `
        <div class="handbook-target-card">
          <div class="target-num-badge" style="background:#e11d48;">${t.code}</div>
          <div class="target-content">
            <span class="target-tag-means">執行方法 (資金/技術/政策)</span>
            <div class="target-desc-text">${t.description}</div>
          </div>
        </div>
      `).join("");

      return `
        <div class="handbook-goal-card" id="goal-anchor-${g.id}" style="border-left: 6px solid ${g.color};">
          <div class="handbook-goal-header" onclick="GameApp.toggleGoalCollapse(${g.id})">
            <div class="handbook-goal-title">
              <div style="font-size:1.6rem; min-width:32px; text-align:center;">${g.icon || "🎯"}</div>
              <div>
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                  <h3 style="color:${g.color}; font-size:1.15rem; font-weight:700; margin:0;">SDG ${g.id} ${g.name}</h3>
                  <span class="handbook-badge-5p">${g.category_zh}領域 (${g.category})</span>
                  <span style="font-size:0.75rem; background:#eff6ff; color:#1d4ed8; padding:2px 8px; border-radius:4px; font-weight:700;">共 ${g.targets_count} 項細項</span>
                </div>
                <div style="font-size:0.85rem; color:#475569; margin-top:3px;">${g.full_name}</div>
                ${g.slogan ? `<div style="font-size:0.78rem; color:#64748b; margin-top:2px;">💡 生活實踐指標：${g.slogan} (${g.example})</div>` : ''}
              </div>
            </div>
            <div id="toggle-icon-${g.id}" style="font-size:1.2rem; color:#94a3b8; font-weight:bold;">▼</div>
          </div>

          <div id="goal-body-${g.id}">
            <!-- 成果目標區塊 -->
            ${outcomes.length > 0 ? `
              <div class="handbook-section-title" style="color:#166534;">
                <span>🎯</span> <strong>要達成什麼（成果目標 - 數字編號）</strong>
                <span style="font-size:0.72rem; color:#64748b; font-weight:normal; margin-left:auto;">${outcomes.length} 項</span>
              </div>
              <div class="handbook-target-list">
                ${outcomeItemsHtml}
              </div>
            ` : ''}

            <!-- 執行方法區塊 -->
            ${means.length > 0 ? `
              <div class="handbook-section-title" style="color:#9f1239;">
                <span>🛠️</span> <strong>怎麼達成（執行方法 - 字母編號，如資金/技術/能力建構）</strong>
                <span style="font-size:0.72rem; color:#64748b; font-weight:normal; margin-left:auto;">${means.length} 項</span>
              </div>
              <div class="handbook-target-list">
                ${meansItemsHtml}
              </div>
            ` : ''}

            ${(outcomes.length === 0 && means.length === 0) ? `
              <div style="padding:1rem; text-align:center; color:#94a3b8; font-size:0.85rem;">無符合搜尋關鍵字之細項</div>
            ` : ''}
          </div>
        </div>
      `;
    }).join("");

    body.innerHTML = `
      <!-- 教材導讀與說明 -->
      <div class="handbook-guide-box">
        <div style="font-weight:700; font-size:0.92rem; margin-bottom:0.35rem; display:flex; align-items:center; gap:0.4rem;">
          <span>📘</span> 怎麼讀這份資料（教材重點延伸）：
        </div>
        <p style="margin-bottom:0.25rem;">
          每個目標底下的細項分成兩種：<strong>數字編號（如 13.1、13.2）</strong>是<strong>「要達成什麼」的成果目標</strong>；
          <strong>英文字母編號（如 13.a、13.b）</strong>是<strong>「怎麼達成」的執行方法</strong>，例如資金、技術與能力建構。
        </p>
        <p style="margin-bottom:0.25rem;">
          細項的期限多數是 2030 年，少數寫著 2020 年或 2025 年，代表當年設定的階段目標，已經到期。<strong>17 個目標是方向，169 項細項才是可以檢核的具體承諾。</strong>
        </p>
        <div style="margin-top:0.4rem; font-size:0.8rem; color:#047857; font-weight:600;">
          5P 對照：人 People（1–5）｜地球 Planet（6、12–15）｜繁榮 Prosperity（7–11）｜和平 Peace（16）｜夥伴 Partnership（17）
        </div>
      </div>

      <!-- 快速導覽列 (1~17 SDGs 色彩按鈕) -->
      <div style="margin-bottom:0.75rem;">
        <div style="font-size:0.78rem; font-weight:700; color:#475569; margin-bottom:0.35rem;">⚡ 快速跳轉至指定目標：</div>
        <div class="handbook-quick-nav">
          ${quickNavHtml}
        </div>
      </div>

      <!-- 工具列：搜尋與 5P 篩選 -->
      <div class="handbook-tools-bar">
        <div style="display:flex; gap:0.35rem; align-items:center; flex-wrap:wrap;">
          <span style="font-size:0.78rem; font-weight:700; color:#475569;">5P 領域：</span>
          <button class="handbook-filter-btn ${filterCategory === 'all' ? 'active' : ''}" onclick="GameApp.setHandbookFilter('all')">全部 (17)</button>
          <button class="handbook-filter-btn ${filterCategory === '人' ? 'active' : ''}" onclick="GameApp.setHandbookFilter('人')">人 People (1-5)</button>
          <button class="handbook-filter-btn ${filterCategory === '地球' ? 'active' : ''}" onclick="GameApp.setHandbookFilter('地球')">地球 Planet (6,12-15)</button>
          <button class="handbook-filter-btn ${filterCategory === '繁榮' ? 'active' : ''}" onclick="GameApp.setHandbookFilter('繁榮')">繁榮 Prosperity (7-11)</button>
          <button class="handbook-filter-btn ${filterCategory === '和平' ? 'active' : ''}" onclick="GameApp.setHandbookFilter('和平')">和平 Peace (16)</button>
          <button class="handbook-filter-btn ${filterCategory === '夥伴' ? 'active' : ''}" onclick="GameApp.setHandbookFilter('夥伴')">夥伴 Partnership (17)</button>
        </div>

        <div style="display:flex; gap:0.5rem; align-items:center;">
          <input type="text" id="handbook-search-input" class="form-input" style="padding:0.35rem 0.75rem; width:180px; font-size:0.82rem;" placeholder="搜尋細項條文或編號..." value="${searchQuery}">
          <button class="btn btn-outline" style="padding:0.35rem 0.65rem; font-size:0.75rem; border-color:#cbd5e1; color:#475569;" onclick="GameApp.toggleAllGoals()">全部折疊/展開</button>
        </div>
      </div>

      <!-- 17 目標與 169 細項內容列表 -->
      <div style="max-height: 56vh; overflow-y: auto; padding-right: 0.25rem;">
        ${goalsHtml || `<div style="text-align:center; padding:2rem; color:#64748b;">無符合篩選條件之目標細項。</div>`}

        <!-- 頁尾教材資料說明 -->
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:0.5rem; padding:1rem; margin-top:1.5rem; font-size:0.78rem; color:#64748b; line-height:1.55;">
          <strong>資料說明：</strong>${data.source_notes}
          <div style="margin-top:0.35rem; color:#94a3b8;">
            課程資訊：SDGs 與氣候行動：17個目標如何連動｜佛光永續學院 × 佛光大學應用科技與設計學院｜講師：戴慶華 Dr. ANDERSON
          </div>
        </div>
      </div>
    `;

    // Bind real-time search input
    const searchInput = document.getElementById("handbook-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.debounce(() => {
          this.renderHandbookContent(this.handbookData, filterCategory, e.target.value);
        }, 300);
      });
    }
  },

  setHandbookFilter(category) {
    const searchInput = document.getElementById("handbook-search-input");
    const q = searchInput ? searchInput.value : "";
    this.renderHandbookContent(this.handbookData, category, q);
  },

  scrollToGoal(goalId) {
    const el = document.getElementById(`goal-anchor-${goalId}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.style.boxShadow = "0 0 0 3px rgba(37,99,235,0.4)";
      setTimeout(() => el.style.boxShadow = "0 2px 5px rgba(0,0,0,0.03)", 1500);
    }
  },

  toggleGoalCollapse(goalId) {
    const body = document.getElementById(`goal-body-${goalId}`);
    const icon = document.getElementById(`toggle-icon-${goalId}`);
    if (body) {
      const isHidden = body.style.display === "none";
      body.style.display = isHidden ? "block" : "none";
      if (icon) icon.innerText = isHidden ? "▼" : "▶";
    }
  },

  toggleAllGoals() {
    this.handbookAllCollapsed = !this.handbookAllCollapsed;
    this.handbookData.goals.forEach(g => {
      const body = document.getElementById(`goal-body-${g.id}`);
      const icon = document.getElementById(`toggle-icon-${g.id}`);
      if (body) {
        body.style.display = this.handbookAllCollapsed ? "none" : "block";
        if (icon) icon.innerText = this.handbookAllCollapsed ? "▶" : "▼";
      }
    });
  },

  debounceTimer: null,
  debounce(func, wait) {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(func, wait);
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
