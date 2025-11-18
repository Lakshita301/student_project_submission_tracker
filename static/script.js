  // static/scripts.js
  function notify(msg) {
    alert(msg);
  }

  function refreshStatus() {
    $.get('/live_status', function(data) {
      let rows = '';
      data.forEach(r => {
        rows += `<tr><td>${r.submission_id}</td><td>${r.student}</td><td>${r.project}</td><td>${r.status}</td><td>${r.submission_date}</td></tr>`;
      });
      $('#liveTable tbody').html(rows);
    });
  }

  setInterval(refreshStatus, 10000);
