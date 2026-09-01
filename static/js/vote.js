// Vanilla JS handler for the prediction vote panel.
//
// The vote panel is progressively enhanced: the server renders the current
// vote state, and this script wires up fetch()-based submission so voting
// doesn't require a full page reload. Django's CSRF protection requires the
// X-CSRFToken header on same-origin fetch/XHR requests; we read the token
// from the `csrftoken` cookie that Django's CsrfViewMiddleware sets.

(function () {
  function getCookie(name) {
    const prefix = name + "=";
    const parts = document.cookie ? document.cookie.split("; ") : [];
    for (const part of parts) {
      if (part.startsWith(prefix)) {
        return decodeURIComponent(part.slice(prefix.length));
      }
    }
    return null;
  }

  function init() {
    const panel = document.getElementById("vote-panel");
    if (!panel) return;

    const voteUrl = panel.dataset.voteUrl;
    const buttons = panel.querySelectorAll(".js-vote-btn");
    const statusEl = document.getElementById("vote-status");
    const useConfidence = document.getElementById("use-confidence");
    const confidenceRow = document.getElementById("confidence-row");
    const confidenceRange = document.getElementById("confidence-range");
    const confidenceValue = document.getElementById("confidence-value");

    let selected = panel.dataset.selected || "";
    highlightSelected(selected);

    if (useConfidence) {
      useConfidence.addEventListener("change", function () {
        if (confidenceRow) {
          confidenceRow.style.display = useConfidence.checked ? "flex" : "none";
        }
      });
    }

    if (confidenceRange && confidenceValue) {
      confidenceRange.addEventListener("input", function () {
        confidenceValue.textContent = confidenceRange.value + "%";
      });
    }

    function highlightSelected(option) {
      buttons.forEach(function (btn) {
        if (btn.dataset.option === option) {
          btn.classList.add("btn-primary");
          btn.classList.remove("btn-outline");
        } else {
          btn.classList.remove("btn-primary");
          btn.classList.add("btn-outline");
        }
      });
    }

    function showStatus(message, isError) {
      if (!statusEl) return;
      statusEl.textContent = message;
      statusEl.classList.toggle("text-no", !!isError);
      statusEl.classList.toggle("text-primary", !isError);
    }

    function labelFor(option) {
      const btn = panel.querySelector('.js-vote-btn[data-option="' + option + '"]');
      return btn ? btn.textContent.trim() : option;
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const option = btn.dataset.option;
        buttons.forEach(function (b) {
          b.disabled = true;
        });

        const payload = { selected_option: option };
        if (useConfidence && useConfidence.checked && confidenceRange) {
          payload.confidence = parseInt(confidenceRange.value, 10);
        }

        fetch(voteUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken") || "",
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (result) {
            buttons.forEach(function (b) {
              b.disabled = false;
            });
            if (!result.ok || result.data.ok === false) {
              const message = (result.data && result.data.error && result.data.error.message) || "予測の送信に失敗しました";
              showStatus(message, true);
              return;
            }
            selected = result.data.selected_option;
            highlightSelected(selected);
            showStatus("現在の予測: " + labelFor(selected) + " — 締切前であれば変更できます", false);
          })
          .catch(function () {
            buttons.forEach(function (b) {
              b.disabled = false;
            });
            showStatus("通信エラーが発生しました。もう一度お試しください。", true);
          });
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
