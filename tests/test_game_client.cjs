const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
  function element() {
    const classes = new Set(['active']);
    const label = { textContent: '點擊配對此目標' };
    return {
      disabled: false, innerText: 'SDG 13',
      classList: { add: value => classes.add(value), remove: value => classes.delete(value), contains: value => classes.has(value) },
      setAttribute(key, value) { this[key] = value; },
      removeAttribute(key) { delete this[key]; },
      querySelector() { return label; },
    };
  }
  const buttons = [element(), element()];
  const modeCards = Object.fromEntries(['scenario', 'standard', 'cards', 'master169'].map(mode => [mode, {
    ...element(), scrollIntoView() {},
  }]));
  const nodes = { 'view-gameplay': element() };
  const scheduled = [];
  let resolve, calls = 0;
  const pending = new Promise(done => { resolve = done; });
  const context = vm.createContext({
    console,
    document: {
      addEventListener() {},
      querySelectorAll: selector => selector === '.mode-card' ? Object.values(modeCards) : buttons,
      querySelector: selector => modeCards[selector.match(/data-mode="([^"]+)"/)?.[1]],
      getElementById: id => nodes[id] ||= element(),
    },
    fetch: () => { calls++; return pending; },
    clearInterval() {},
    setTimeout: (callback, delay) => scheduled.push({ callback, delay }),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/js/game.js'), 'utf8'), context);
  const app = vm.runInContext('GameApp', context);
  vm.runInContext('SoundEffects.correct = SoundEffects.wrong = SoundEffects.combo = () => {}', context);
  app.state.sessionId = 1;
  app.updateScoreDisplay = () => {};
  let explanations = 0;
  app.showExplanationModal = () => { explanations++; };
  const question = { correct_goal_id: 13, target_id: 1 };
  const response = { ok: true, json: async () => ({ is_correct: true, new_combo: 1, score_delta: 100 }) };
  return { app, buttons, modeCards, nodes, question, scheduled, response, resolve, calls: () => calls, explanations: () => explanations };
}

test('a click shows feedback immediately and repeated clicks submit once', async () => {
  const h = setup();
  const answer = h.app.handleOptionClick(h.buttons[0], 13, h.question);
  assert.equal(h.buttons[0].querySelector().textContent, '已選擇，正在判定…');
  assert.equal(h.buttons[0].classList.contains('pending'), true);
  assert.equal(h.buttons[0]['aria-busy'], 'true');
  assert.ok(h.buttons.every(button => button.disabled));
  await h.app.handleOptionClick(h.buttons[0], 13, h.question);
  assert.equal(h.calls(), 1);
  h.resolve(h.response);
  await answer;
  assert.equal(h.app.state.score, 100);
  assert.equal(h.buttons[0].classList.contains('pending'), false);
  assert.equal(h.scheduled.length, 1);
  assert.ok(h.scheduled[0].delay <= 250);
});

test('an old response cannot change the score after leaving the game', async () => {
  const h = setup();
  const answer = h.app.handleOptionClick(h.buttons[0], 13, h.question);
  h.nodes['view-gameplay'].classList.remove('active');
  h.resolve(h.response);
  await answer;
  assert.equal(h.app.state.score, 0);
  assert.equal(h.scheduled.length, 0);
});

test('a delayed explanation does not open over a new question', async () => {
  const h = setup();
  const answer = h.app.handleOptionClick(h.buttons[0], 13, h.question);
  h.resolve(h.response);
  await answer;
  h.app.state.currentIndex++;
  h.scheduled[0].callback();
  assert.equal(h.explanations(), 0);
});

test('all four leaderboard tabs have a matching game button with or without records', async () => {
  for (const mode of ['scenario', 'standard', 'cards', 'master169']) {
    for (const list of [[], [{ mode, nickname: 'tester', total_score: 100 }]]) {
      const h = setup();
      const loading = h.app.loadLeaderboardData(mode);
      h.resolve({ json: async () => list });
      await loading;
      const html = h.nodes['leaderboard-tab-content'].innerHTML;
      assert.ok(html.includes(`GameApp.selectModeAndStart('${mode}')`), `${mode}, records: ${list.length}`);
      assert.ok(html.includes(`立即挑戰「${h.app.MODE_NAMES[mode]}」`));
      assert.equal((html.match(/selectModeAndStart/g) || []).length, 1);
    }
  }
});

test('leaderboard game buttons return to the lobby and select the matching mode', () => {
  const h = setup();
  h.nodes['input-nickname'] = { value: 'tester' };
  for (const mode of ['scenario', 'standard', 'cards', 'master169']) {
    h.app.selectModeAndStart(mode);
    assert.equal(h.app.state.selectedMode, mode);
    assert.ok(h.modeCards[mode].classList.contains('selected'));
    assert.equal(h.nodes['view-gameplay'].classList.contains('active'), false);
    assert.ok(h.nodes['view-welcome'].classList.contains('active'));
    for (const other of Object.keys(h.modeCards).filter(item => item !== mode)) {
      assert.equal(h.modeCards[other].classList.contains('selected'), false);
    }
  }
});
