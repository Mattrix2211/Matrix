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
const ecouteursParType = {};
global.window = { addEventListener() {} };
global.document = {
  readyState: 'complete',
  addEventListener(type, fn) { ecouteurs++; (ecouteursParType[type] = ecouteursParType[type] || []).push(fn); },
  querySelectorAll() { return []; }
};
delete require.cache[require.resolve('../static/js/grille.js')];
require('../static/js/grille.js');
// « Tout conforme » sans cellule active : toute la colonne de conformité, valeurs saisies conservées.
function champ(valeur, conformite) {
  const attrs = conformite ? { 'data-conformite': '', 'data-grille-champ': '' } : { 'data-grille-champ': '' };
  return {
    tagName: 'SELECT', value: valeur, options: [{ value: 'conforme' }, { value: 'non_conforme' }],
    hasAttribute(n) { return n in attrs; }, getAttribute(n) { return n in attrs ? attrs[n] : null; },
    closest() { return null; }
  };
}
const colonne = [champ('', true), champ('non_conforme', true), champ('', true)];
const texte = [champ('', false), champ('', false), champ('', false)];
const lignes = colonne.map((c, i) => ({ querySelectorAll() { return [c, texte[i]]; } }));
const grille = { querySelectorAll(sel) { return sel === 'tbody tr' ? lignes : []; } }; // aucune cellule active
const bouton = {
  getAttribute() { return 'tout-conforme'; },
  closest(sel) { return sel === '[data-grille]' ? grille : bouton; }
};
ecouteursParType.click.forEach(fn => fn({ target: bouton }));
assert.deepStrictEqual(colonne.map(c => c.value), ['conforme', 'non_conforme', 'conforme']);
assert.deepStrictEqual(texte.map(c => c.value), ['', '', '']);

const premier = ecouteurs;
assert.ok(premier > 0);
delete require.cache[require.resolve('../static/js/grille.js')];
require('../static/js/grille.js');
assert.strictEqual(ecouteurs, premier);
console.log('ok');
