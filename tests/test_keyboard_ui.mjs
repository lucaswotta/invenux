import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../ui/index.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
let focused = null;
class Row {
  constructor() {
    this.dataset = {};
    this.attributes = {};
    this.tabIndex = -1;
    this.classList = { toggle() {} };
  }
  set innerHTML(value) { this.html = value; }
  get nextSibling() { return tbody.children[tbody.children.indexOf(this) + 1] || null; }
  get parentElement() { return tbody; }
  remove() { tbody.children.splice(tbody.children.indexOf(this), 1); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  closest() { return this; }
  focus() { focused = this; }
}
const tbody = {
  children: [],
  querySelectorAll() { return this.children; },
  replaceChildren() { this.children = []; },
  get firstChild() { return this.children[0] || null; },
  insertBefore(row, next) {
    if (this.children.includes(row)) row.remove();
    this.children.splice(next ? this.children.indexOf(next) : this.children.length, 0, row);
  },
};
const inspector = { focus() { focused = inspector; } };
const banner = { dataset: {}, writes: 0, set innerHTML(value) { this.writes++; } };
const elements = new Map([
  ['hosts-tbody', tbody], ['inspector-pane', inspector], ['status-banner', banner],
  ['i18n-catalog', { textContent: '{}' }],
]);
const context = vm.createContext({
  console,
  matchMedia: () => ({ addEventListener() {} }),
  window: { addEventListener() {}, __INVENUX_TOKEN__: '' },
  document: {
    addEventListener() {},
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, { value: '', textContent: '', classList: { toggle() {} } });
      return elements.get(id);
    },
    createElement() { return new Row(); },
  },
  setInterval() {}, clearInterval() {}, setTimeout() {}, clearTimeout() {},
});
vm.runInContext(script, context);
vm.runInContext(`
  tr = key => key;
  renderOnboarding = renderInspector = () => {};
  appState.records = Array.from({length: 30}, (_, index) => ({ip: 'host-' + index, status: 'ONLINE'}));
  renderScanTable();
`, context);

const tabbable = () => tbody.children.filter(row => row.tabIndex === 0).map(row => row.dataset.ip);
assert.deepEqual(tabbable(), ['host-0']);
assert.equal(tbody.children[0].attributes['aria-current'], 'true');

const press = (row, key) => {
  let prevented = false;
  context.moveRowFocus({ key, target: row, preventDefault() { prevented = true; } });
  return prevented;
};
assert.equal(press(tbody.children[0], 'ArrowDown'), true);
assert.deepEqual(tabbable(), ['host-1']);
assert.equal(focused, tbody.children[1]);
assert.equal(tbody.children[0].attributes['aria-current'], undefined);
press(tbody.children[1], 'End');
assert.deepEqual(tabbable(), ['host-29']);
press(tbody.children[29], 'ArrowDown');
assert.deepEqual(tabbable(), ['host-29']);
press(tbody.children[29], 'PageUp');
assert.deepEqual(tabbable(), ['host-19']);
press(tbody.children[19], 'Home');
assert.deepEqual(tabbable(), ['host-0']);
assert.equal(press(tbody.children[0], 'a'), false);
press(tbody.children[4], 'Enter');
assert.deepEqual(tabbable(), ['host-4']);
assert.equal(focused, inspector);
console.log('PASS: one tabbable row, arrows/Home/End/PageUp move it, Enter opens the details');

vm.runInContext(`setBanner('Collecting 1/2'); setBanner('Collecting 1/2'); setBanner('Collecting 2/2');`, context);
assert.equal(banner.writes, 2);
console.log('PASS: the live banner is rewritten only when its text changes');
