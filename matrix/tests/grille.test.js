// Test de la logique pure de static/js/grille.js : node matrix/tests/grille.test.js
const assert = require('assert');
const g = require('../static/js/grille.js');

assert.deepStrictEqual(g.decouperPresse('a\tb\r\nc\td\r\n'), [['a', 'b'], ['c', 'd']]);
assert.deepStrictEqual(g.decouperPresse('x'), [['x']]);
assert.deepStrictEqual(g.decouperPresse('1\n2\n3'), [['1'], ['2'], ['3']]);

assert.deepStrictEqual(g.deplacer('Enter', 0, 1, 3, 4), { ligne: 1, colonne: 1 });
assert.deepStrictEqual(g.deplacer('Enter', 2, 1, 3, 4), { ligne: 2, colonne: 1 });
assert.deepStrictEqual(g.deplacer('ArrowLeft', 0, 0, 3, 4), { ligne: 0, colonne: 0 });
assert.deepStrictEqual(g.deplacer('ArrowRight', 1, 2, 3, 4), { ligne: 1, colonne: 3 });
assert.deepStrictEqual(g.deplacer('ArrowUp', 0, 2, 3, 4), { ligne: 0, colonne: 2 });
assert.strictEqual(g.deplacer('a', 0, 0, 3, 4), null);

assert.deepStrictEqual(
  g.toutConforme(['', 'non_conforme', 'non_applicable', '', 'conforme']),
  ['conforme', 'non_conforme', 'non_applicable', 'conforme', 'conforme']
);
assert.strictEqual(g.horsPlage('12,5', '0', '10'), true);
assert.strictEqual(g.horsPlage('5', '0', '10'), false);
assert.strictEqual(g.horsPlage('-1', '0', null), true);
assert.strictEqual(g.horsPlage('', '0', '10'), false);
assert.strictEqual(g.horsPlage('abc', '0', '10'), false);
// Garde anti-doublon : un second chargement du script ne réinstalle rien.
let ecouteurs = 0;
global.window = {};
global.document = {
  readyState: 'complete',
  addEventListener() { ecouteurs++; },
  querySelectorAll() { return []; }
};
delete require.cache[require.resolve('../static/js/grille.js')];
require('../static/js/grille.js');
const premier = ecouteurs;
assert.ok(premier > 0);
delete require.cache[require.resolve('../static/js/grille.js')];
require('../static/js/grille.js');
assert.strictEqual(ecouteurs, premier);
console.log('ok');
