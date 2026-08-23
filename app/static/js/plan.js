(function () {
  const modal = document.getElementById("key-modal");
  const copyBtn = document.getElementById("copy-key-btn");
  const closeBtn = document.getElementById("close-key-modal");
  const ackBtn = document.getElementById("ack-key-btn");
  const keyEl = document.getElementById("access-key-value");

  if (!modal) return;

  if (copyBtn && keyEl) {
    copyBtn.addEventListener("click", function () {
      navigator.clipboard.writeText(keyEl.textContent.trim()).then(function () {
        copyBtn.textContent = "Copied!";
        setTimeout(function () { copyBtn.textContent = "Copy key"; }, 2000);
      });
    });
  }

  const dismissBtn = closeBtn || ackBtn;
  if (dismissBtn) {
    dismissBtn.addEventListener("click", function () {
      modal.style.display = "none";
      const url = new URL(window.location.href);
      url.searchParams.delete("approved");
      window.history.replaceState({}, "", url.pathname);
    });
  }
})();
