buildScene($("#scene")).setSun(1);
initAccount(user => {
  if (user) $("#greet").textContent = "Welcome in, " + (user.display_name || user.email.split("@")[0]) + ". Take your time.";
});
