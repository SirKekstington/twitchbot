let lastNonce = null;

async function fetchWinner() {
  try {
    const response = await fetch("winner.json?cache=" + Date.now());

    if (!response.ok) {
      return;
    }

    const data = await response.json();

    if (!data.winner) {
      return;
    }

    if (data.nonce === lastNonce) {
      return;
    }

    lastNonce = data.nonce;

    showWinner(data);
  } catch (error) {
    console.error("Could not load winner.json", error);
  }
}

function showWinner(data) {
  const overlay = document.getElementById("overlay");
  const winner = document.getElementById("winner");
  const meta = document.getElementById("meta");

  winner.textContent = data.winner;

  meta.textContent = `${data.total_entries} Teilnehmer · ${data.timestamp}`;

  overlay.classList.remove("hidden");
  overlay.classList.add("show");

  setTimeout(() => {
    overlay.classList.remove("show");
    overlay.classList.add("hidden");
  }, 10000);
}

setInterval(fetchWinner, 1000);
fetchWinner();
