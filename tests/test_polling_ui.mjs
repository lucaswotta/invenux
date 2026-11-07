import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../ui/index.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
let writes = 0;
class Row {
  constructor() {
    this.dataset = {};
    this.classList = { toggle() {} };
  }
  set innerHTML(value) { this.html = value; writes++; }
  get nextSibling() { return tbody.children[tbody.children.indexOf(this) + 1] || null; }
  remove() { tbody.children.splice(tbody.children.indexOf(this), 1); }
}
const tbody = {
  children: [],
  scrollTop: 1200,
  querySelectorAll() { return this.children; },
  replaceChildren() { this.children = []; },
  get firstChild() { return this.children[0] || null; },
  insertBefore(row, next) {
    if (this.children.includes(row)) row.remove();
    this.children.splice(next ? this.children.indexOf(next) : this.children.length, 0, row);
  },
};
const elements = new Map([['hosts-tbody', tbody], ['i18n-catalog', {textContent: '{}'}]]);
const context = vm.createContext({
  console,
  matchMedia: () => ({addEventListener() {}}),
  window: { addEventListener() {}, matchMedia: () => ({ matches: false }), __INVENUX_TOKEN__: '' },
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
  renderOnboarding = renderInspector = renderTargetSummary = updateToolbarAndFooter =
    renderDashboard = renderSnapshots = setBanner = () => {};
  appState.records = Array.from({length: 3000}, (_, index) => ({ip: 'host-' + index, status: 'PENDING'}));
  appState.revision = 1;
  renderScanTable();
`, context);
assert.equal(tbody.children.length, 3000);
assert.equal(writes, 3000);
const first = tbody.children[0];
const last = tbody.children[2999];
writes = 0;
vm.runInContext(`applyServerState({revision: 2, reset: false, scanning: true,
  records: [{ip: 'host-1500', status: 'ONLINE', ram: '8 GiB'}]});`, context);
assert.equal(writes, 1);
assert.equal(tbody.children[0], first);
assert.equal(tbody.children[2999], last);
assert.equal(tbody.scrollTop, 1200);
assert.match(tbody.children[1500].html, /8 GiB/);
writes = 0;
vm.runInContext(`applyServerState({revision: 1, reset: true, records: []});
  applyServerState({revision: 2, reset: false, records: []});`, context);
assert.equal(tbody.children.length, 3000);
assert.equal(writes, 0);
vm.runInContext(`appState.statusFilter = 'ONLINE'; renderScanTable();`, context);
assert.equal(tbody.children.length, 1);
assert.equal(tbody.children[0].dataset.ip, 'host-1500');
vm.runInContext(`appState.statusFilter = 'ALL'; renderScanTable();`, context);
assert.equal(tbody.children.length, 3000);
assert.equal(tbody.children[1500].dataset.ip, 'host-1500');
console.log('PASS: 3000 rows, one changed row, stable nodes, stale responses and filters');
let scheduled;
let resolveRequest;
context.setTimeout = callback => { scheduled = callback; return 1; };
context.fetch = async () => new Promise(resolve => { resolveRequest = resolve; });
vm.runInContext('startPolling()', context);
const poll = scheduled;
scheduled = null;
const pending = poll();
assert.equal(scheduled, null);
resolveRequest({ok: true, json: async () => ({revision: 3, reset: false, records: [], scanning: false, more: true})});
await pending;
assert.equal(typeof scheduled, 'function');
const finalPoll = scheduled;
scheduled = null;
const finished = finalPoll();
resolveRequest({ok: true, json: async () => ({revision: 3, reset: false, records: [], scanning: false, more: false})});
await finished;
assert.equal(scheduled, null);
console.log('PASS: requests do not overlap and polling drains the final backlog');
