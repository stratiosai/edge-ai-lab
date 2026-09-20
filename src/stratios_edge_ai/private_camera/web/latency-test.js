const clock = document.querySelector("#clock");

function renderClock() {
  const now = new Date();
  const time = now.toLocaleTimeString([], {hour12:false});
  clock.textContent = time;
  requestAnimationFrame(renderClock);
}

requestAnimationFrame(renderClock);
