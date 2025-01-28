// Play audio functionality
document.querySelector('.btn-reset')?.addEventListener('click', function() {
    const audio = new Audio(src='{{result}}');
    
    // Add visual feedback
    this.classList.add('pulse');
    
    audio.play().then(() => {
        // Remove animation when audio ends
        audio.onended = () => this.classList.remove('pulse');
    }).catch(error => {
        console.error('Error playing audio:', error);
        this.classList.remove('pulse');
    });
});

// File upload preview
const fileInput = document.querySelector('.form-input');
const fileLabel = document.querySelector('.form-descr');

if (fileInput) {
    fileInput.addEventListener('change', function(e) {
        if (this.files && this.files[0]) {
            fileLabel.textContent = `Selected file: ${this.files[0].name}`;
            fileLabel.classList.add('fade-in');
        }
    });
}

// Add drag and drop support
const dropZone = document.querySelector('.form-file');
if (dropZone) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('highlight');
    }

    function unhighlight(e) {
        dropZone.classList.remove('highlight');
    }
}

// ../static/voice/voice_8.mp3