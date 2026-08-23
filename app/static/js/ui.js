(function () {
  'use strict';

  function initChipGroups() {
    document.querySelectorAll('.check-group').forEach((group) => {
      const name = group.dataset.group;
      if (!name) return;

      const selected = new Set();
      group.querySelectorAll('input[type="hidden"][name="' + name + '"]').forEach((input) => {
        selected.add(input.value);
      });

      group.querySelectorAll('.chip').forEach((chip) => {
        const value = chip.dataset.value;
        const isOn = selected.has(value);
        chip.dataset.selected = isOn ? 'true' : 'false';
        chip.setAttribute('aria-pressed', isOn ? 'true' : 'false');
      });

      group.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip || !group.contains(chip)) return;

        const value = chip.dataset.value;
        if (selected.has(value)) {
          selected.delete(value);
          chip.dataset.selected = 'false';
          chip.setAttribute('aria-pressed', 'false');
        } else {
          selected.add(value);
          chip.dataset.selected = 'true';
          chip.setAttribute('aria-pressed', 'true');
        }
        syncHidden(group, name, selected);
      });
    });
  }

  function syncHidden(group, name, selected) {
    group.querySelectorAll('input[type="hidden"][name="' + name + '"]').forEach((n) => n.remove());
    selected.forEach((v) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = name;
      input.value = v;
      group.appendChild(input);
    });
  }

  function initSectionReveal() {
    document.querySelectorAll('.section, .question-card, .app-card').forEach((el, i) => {
      el.style.animationDelay = `${i * 0.04}s`;
      el.classList.add('reveal');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initChipGroups();
    initSectionReveal();
  });
})();
