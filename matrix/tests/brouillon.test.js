// Test de la logique pure de static/js/brouillon.js : node matrix/tests/brouillon.test.js
const assert = require('assert');
const b = require('../static/js/brouillon.js');

assert.strictEqual(b.nomSensible('password'), true);
assert.strictEqual(b.nomSensible('new_password1'), true);
assert.strictEqual(b.nomSensible('csrfmiddlewaretoken'), true);
assert.strictEqual(b.nomSensible('mot_de_passe_signature'), true);
assert.strictEqual(b.nomSensible('observations'), false);
assert.strictEqual(b.nomSensible('passage'), false);
assert.strictEqual(b.nomSensible('compass'), false);
assert.strictEqual(b.nomSensible('api_token'), true);
assert.strictEqual(b.nomSensible(''), false);

assert.deepStrictEqual([0, 1, 2, 3, 4, 10].map(b.delaiReessai), [5000, 10000, 20000, 40000, 60000, 60000]);
assert.strictEqual(b.delaiReessai(-3), 5000);

assert.strictEqual(b.formaterHeure(new Date(2026, 9, 2, 9, 5)), '09:05');
assert.strictEqual(b.formaterHeure(b.dateMurale('2026-10-07T19:23:41+02:00')), '19:23');
assert.strictEqual(b.formaterDateHeure(new Date(2026, 9, 2, 14, 12)), '02/10 à 14:12');

assert.strictEqual(b.contenuVide({ a: '', b: [] }), true);
assert.strictEqual(b.contenuVide({ a: '', b: ['x'] }), false);
assert.strictEqual(b.contenuVide({}), true);

// Garde anti-doublon : un second chargement du script ne réinstalle rien.
let ecouteurs = 0;
global.window = { addEventListener() { ecouteurs++; } };
global.document = {
  readyState: 'complete',
  cookie: '',
  addEventListener() { ecouteurs++; },
  querySelectorAll() { return []; }
};
global.sessionStorage = { getItem() { return null; } };
delete require.cache[require.resolve('../static/js/brouillon.js')];
require('../static/js/brouillon.js');
const premier = ecouteurs;
assert.ok(premier > 0);
delete require.cache[require.resolve('../static/js/brouillon.js')];
require('../static/js/brouillon.js');
assert.strictEqual(ecouteurs, premier);
console.log('brouillon.test.js : OK');
