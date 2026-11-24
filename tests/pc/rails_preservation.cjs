const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'pc/bp_public_controls.js'), 'utf8');
const context = vm.createContext({ DFL: { appActionButtonClasses: {} } });
vm.runInContext(source.slice(source.indexOf('function translateHubTheme('), source.indexOf('const PC_GAME_STYLES')), context);
const styles = JSON.parse(fs.readFileSync(path.join(root, 'pc/assets/game_styles.json'), 'utf8'));
for (const app of ['2531310', '2124490', '1903340', '1689620', '2129530']) {
  context.row = styles[app];
  const css = vm.runInContext('translateHubTheme(row.cls,row.css,1080)', context);
  const railRules = css.split('\n').filter(rule => /\.gh-rule/.test(rule));
  assert.ok(railRules.length, `${app}: legacy ornament missing`);
  assert.ok(railRules.every(rule => rule.includes('.gh-rule:not(.gh-has-rail)')), `${app}: old background targets loaded PNG`);
}
console.log('PASS legacy rail/background rules exclude loaded PNG containers; old ornaments remain available');
