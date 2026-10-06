// Logique pure de static/js/inactivite.js : node matrix/tests/inactivite.test.js
const assert = require('assert');
const { phase, secondesRestantes, renouvellementUtile, serveurToujoursValide } = require('../static/js/inactivite.js');

// Délai 100 s, préavis 20 s (valeurs d'essai : le script n'en connaît aucune)
assert.strictEqual(phase(0, 0, 100000, 20000), 'actif');
assert.strictEqual(phase(79000, 0, 100000, 20000), 'actif');
assert.strictEqual(phase(80000, 0, 100000, 20000), 'avertissement');
assert.strictEqual(phase(99999, 0, 100000, 20000), 'avertissement');
assert.strictEqual(phase(100000, 0, 100000, 20000), 'expire');

assert.strictEqual(secondesRestantes(80000, 0, 100000), 20);
assert.strictEqual(secondesRestantes(80001, 0, 100000), 20);
assert.strictEqual(secondesRestantes(120000, 0, 100000), 0);

assert.strictEqual(renouvellementUtile(9999, 0, 20000), false);
assert.strictEqual(renouvellementUtile(10000, 0, 20000), true);

assert.strictEqual(serveurToujoursValide(9000, 20000), false);
assert.strictEqual(serveurToujoursValide(60000, 20000), true);
console.log('inactivite.test.js : OK');
