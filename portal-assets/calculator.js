(() => {
  'use strict';
  const form = document.getElementById('unit-form'), C = window.PortalCommerce;
  if (!form || !C) return;
  const config = JSON.parse(form.dataset.config);
  const output = document.getElementById('calc-result'), mode = document.getElementById('calc-mode');
  const fields = ['price', 'shipping', 'coupon', 'quantity', ...(config.dose ? ['dose'] : [])];
  const format = n => new Intl.NumberFormat('ja-JP', {maximumFractionDigits: 3}).format(n);
  let attempted = false;
  const read = prefix => Object.fromEntries(fields.map(name => {
    const input = form.elements.namedItem(prefix + '-' + name);
    const value = input.value.trim() === '' ? (name === 'shipping' || name === 'coupon' ? 0 : NaN) : Number(input.value);
    input.removeAttribute('aria-invalid');
    return [name, value];
  }));
  function calculate() {
    attempted = true;
    const a = C.unitCost(read('a')), b = C.unitCost(read('b'));
    if (!a || !b) {
      output.textContent = '商品代・送料・クーポンは0以上、量と使用量は0より大きい数字で入力してください。クーポンは商品代と送料の合計以下にしてください。';
      output.classList.add('input-error');
      for (const input of form.querySelectorAll('input')) {
        const v = Number(input.value), positive = /quantity|dose/.test(input.name);
        if (input.value === '' || !Number.isFinite(v) || v < 0 || (positive && v <= 0)) input.setAttribute('aria-invalid', 'true');
      }
      return;
    }
    output.classList.remove('input-error');
    const av = config.dose ? a.perUse : a.unit, bv = config.dose ? b.perUse : b.unit;
    const unit = config.dose ? '回' : config.unit;
    const difference = Math.abs(av - bv);
    const message = difference < 0.00000001 ? '単価は同じです。' :
      '候補' + (av < bv ? 'A' : 'B') + 'が1' + unit + '当たり' + format(difference) + '円安い計算です。';
    output.innerHTML = '<div class="calculator-totals"><div><span>候補A</span><strong>' + format(av) + '円 / ' + C.escape(unit) +
      '</strong><small>支払額 ' + format(a.total) + '円</small></div><div><span>候補B</span><strong>' + format(bv) + '円 / ' + C.escape(unit) +
      '</strong><small>支払額 ' + format(b.total) + '円</small></div></div><p>' + C.escape(message) + '</p>';
  }
  form.addEventListener('submit', event => {event.preventDefault(); calculate();});
  form.addEventListener('input', () => {mode.textContent = ''; if (attempted) calculate();});
  document.getElementById('calc-example').addEventListener('click', () => {
    for (const [index, prefix] of ['a', 'b'].entries()) {
      fields.forEach((field, i) => {form.elements.namedItem(prefix + '-' + field).value = config.example[index][i];});
    }
    mode.textContent = '架空の例を入力しています。実際の商品価格・使用量ではありません。';
    calculate();
  });
  form.addEventListener('reset', () => {
    attempted = false;
    output.textContent = '2つの候補を入力すると、単価と差額がここに表示されます。';
    output.classList.remove('input-error'); mode.textContent = '';
    form.querySelectorAll('[aria-invalid]').forEach(input => input.removeAttribute('aria-invalid'));
  });
})();
