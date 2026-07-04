
  (function() {
    const fileInput = document.getElementById('fileInput');
    const fileNameDisplay = document.getElementById('file-name-display');
    const filePickerBtn = document.getElementById('filePickerBtn');
    const uploadForm = document.getElementById('uploadForm');
    const statusMsg = document.getElementById('formStatus');

    // --- 1. sync filename with custom display ---
    function updateFileName() {
      const files = fileInput.files;
      if (files && files.length > 0) {
        const name = files[0].name;
        // truncate if too long (optional)
        fileNameDisplay.textContent = name.length > 28 ? name.slice(0, 25) + '…' : name;
        fileNameDisplay.classList.remove('file-name-placeholder');
        // clear any previous status
        statusMsg.textContent = '';
      } else {
        fileNameDisplay.textContent = 'No file selected';
        fileNameDisplay.classList.add('file-name-placeholder');
      }
    }

    // trigger update on change
    fileInput.addEventListener('change', updateFileName);

    // --- 2. click on custom button triggers file input ---
    filePickerBtn.addEventListener('click', function(e) {
      e.preventDefault();
      fileInput.click();  // open native file dialog
    });

    // also handle label click (for accessibility)
    // but we already have the button, fine.

    // --- 3. form submit: demo feedback (prevent actual post) ---
    uploadForm.addEventListener('submit', function(e) {
      e.preventDefault();  // block page reload / POST

      const files = fileInput.files;
      if (!files || files.length === 0) {
        statusMsg.textContent = '⚠️ Please select a file first.';
        statusMsg.style.color = '#b15a3c';
        statusMsg.style.background = 'rgba(200, 70, 40, 0.06)';
        return;
      }

      const fileName = files[0].name;
      const fileSize = (files[0].size / 1024).toFixed(1);
      statusMsg.style.color = '#146b3a';
      statusMsg.style.background = 'rgba(30, 160, 80, 0.08)';
      statusMsg.textContent = `✅ "${fileName}" (${fileSize} KB) – upload simulated (native demo)`;

      // you could actually submit via FormData here if needed.
      // for pure demo we just show feedback.
    });

    // optional: reset status when user selects new file
    fileInput.addEventListener('change', function() {
      statusMsg.textContent = '';
      statusMsg.style.color = '#1d5f7a';
      statusMsg.style.background = 'rgba(0, 100, 150, 0.04)';
    });

    // init: set placeholder if no file
    updateFileName();

    // (optional) extra: if user clears file via same input, update
    // already handled by 'change' event

  })();
