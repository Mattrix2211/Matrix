// Test de la logique pure de static/js/compte_rendu.js : node matrix/tests/compte_rendu.test.js
const assert = require('assert');
const c = require('../static/js/compte_rendu.js');

assert.strictEqual(c.lireNombre('4,2'), 4.2);
assert.strictEqual(c.lireNombre(' 1 250,5 '), 1250.5);
assert.strictEqual(c.lireNombre(''), null);
assert.ok(isNaN(c.lireNombre('abc')));

assert.strictEqual(c.horsPlage(5, 1, 4), true);
assert.strictEqual(c.horsPlage(0.5, 1, 4), true);
assert.strictEqual(c.horsPlage(4, 1, 4), false);
assert.strictEqual(c.horsPlage(9, null, null), false);
assert.strictEqual(c.horsPlage(null, 1, 4), false);

assert.strictEqual(c.conformiteProposee(1, 1), 'NON_CONFORME');
assert.strictEqual(c.conformiteProposee(0, 2), 'A_SURVEILLER');
assert.strictEqual(c.conformiteProposee(0, 0), 'CONFORME');

assert.strictEqual(c.resume(12, 12, 0, 1), '12/12 contrôles, 1 relevé à surveiller');
assert.strictEqual(c.resume(8, 6, 2, 0), '6/8 contrôles, 2 non conformes');
assert.strictEqual(c.resume(0, 0, 0, 0), 'Aucun point à contrôler');

assert.strictEqual(c.formaterDuree(65 * 60000), '1 h 05');
assert.strictEqual(c.formaterDuree(20 * 60000), '20 min');
assert.strictEqual(c.formaterDuree(-5), '');
console.log('ok');
