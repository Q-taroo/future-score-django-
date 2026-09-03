document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;

    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    button.textContent = showing ? "表示" : "隠す";
    button.setAttribute("aria-pressed", String(!showing));
    button.setAttribute("aria-label", showing ? "パスワードを表示" : "パスワードを隠す");
  });
});
