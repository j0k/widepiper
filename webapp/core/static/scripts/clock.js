function fetchServerTimeAndNextBlockTime() {
  // Get current timestamp in milliseconds
  const timerElement_start = document.getElementById('synced-server-time');
  timerElement_start.textContent = 'Fetching...';
  const success = res => res.ok ? res.json() : Promise.resolve({});
  const clientTimestamp = Date.now();
  
  const GetTime = fetch(`/api/v1/get_time?ct=${clientTimestamp}`)
      .then(success)
      .catch(() => { return { error: 'Server error' }; });

  const BlockTime = fetch(`/api/v1/get_next_bet_sync_time`)
      .then(success)
      .catch(() => { return { error: 'Server error' }; });

  return Promise.all([GetTime, BlockTime])
      .then(([GetTime, BlockTime]) => {
          if (GetTime.error || BlockTime.error) {
              timerElement_start.textContent = 'Server error';
              return;
          }

          const serverClientRequestDiffTime = GetTime.diff;
          const serverTimestamp = GetTime.serverTimestamp;
          const serverClientResponseDiffTime = clientTimestamp - serverTimestamp;
          const responseTime = (serverClientRequestDiffTime - clientTimestamp + serverTimestamp - serverClientResponseDiffTime) / 2;
          const syncedServerTime = clientTimestamp + (serverClientResponseDiffTime - responseTime);

          const timeNextBlock = BlockTime.nextBetSync; // assume nextBlockTime is the key in the response
          let remainderTime = timeNextBlock - syncedServerTime;

          // Create separate spans for hours, minutes, and seconds
          const remainSpan = document.createElement('span');
          const minutesSpan = document.createElement('span');
          minutesSpan.id = 'minutes-timer';

          timerElement_start.textContent = ""
          timerElement_start.appendChild(remainSpan);
          timerElement_start.appendChild(minutesSpan);

          // Function to update the timer
          function updateTimer() {
              if (remainderTime <= 0) {
                  clearInterval(timerInterval); // Stop the interval when time is up
                  fetchServerTimeAndNextBlockTime();
              } else {
                  const hours = Math.floor(remainderTime / (1000 * 60 * 60));
                  const minutes = Math.floor((remainderTime % (1000 * 60 * 60)) / (1000 * 60));
                  const seconds = Math.floor((remainderTime % (1000 * 60)) / 1000);

                  remainSpan.textContent = `Next block in `;
                  minutesSpan.textContent = `${minutes}:${seconds < 10 ? `0${seconds}` : seconds}`;
                  

                  remainderTime -= 1000; // Decrease the time by 1 second
              }
          }

          // Update the timer every second
          const timerInterval = setInterval(updateTimer, 1000);
          updateTimer(); // Initial call to display the time immediately
      });
}

fetchServerTimeAndNextBlockTime();
