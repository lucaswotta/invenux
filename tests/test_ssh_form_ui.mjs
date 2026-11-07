import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../ui/index.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements = new Map([['i18n-catalog', { textContent: '{}' }]]);
const sent = [];
const context = vm.createContext({
  console,
  matchMedia: () => ({ addEventListener() {} }),
  window: { addEventListener() {}, __INVENUX_TOKEN__: '' },
  document: {
    addEventListener() {},
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, { value: '', checked: true, dataset: {}, textContent: '', classList: { toggle() {} } });
      return elements.get(id);
    },
  },
  fetch: async (path, options) => {
    sent.push(JSON.parse(options.body));
    return { ok: true, json: async () => ({ config: { has_password: true } }) };
  },
  setInterval() {}, clearInterval() {}, setTimeout() {}, clearTimeout() {},
});
vm.runInContext(script, context);
vm.runInContext('updateToolbarAndFooter = () => {};', context);

// A reloaded page has an empty field while the server keeps the password.
context.document.getElementById('input-ssh-user').value = 'inventory';
await vm.runInContext('syncSshSettings()', context);
assert.equal('ssh_pass' in sent[0], false);

const pass = context.document.getElementById('input-ssh-pass');
pass.dataset.edited = '1';
pass.value = '';
await vm.runInContext('syncSshSettings()', context);
assert.equal(sent[1].ssh_pass, '');
console.log('PASS: an untouched password field never clears the password held by the server');
