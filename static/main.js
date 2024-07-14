document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('send-button').addEventListener('click', function() {
        sendMessage();
    });

    document.getElementById('search-input').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    document.getElementById('search-input').addEventListener('input', function() {
        autoResizeTextarea(this);
    });

    document.getElementById('start-spider-btn').addEventListener('click', function() {
        initiateSpiderSetup();
    });

    document.getElementById('stop-spider-btn').addEventListener('click', function() {
        stopSpider();
    });
});

let spiderConfig = {};

function sendMessage() {
    const inputElement = document.getElementById('search-input');
    const message = inputElement.value.trim();
    if (message !== '') {
        addMessage(message, 'user');
        inputElement.value = '';
        inputElement.style.height = '20px'; // Reset height

        // Handle spider commands
        if (message.startsWith('start spider')) {
            initiateSpiderSetup();
        } else if (message.startsWith('stop spider')) {
            stopSpider();
        } else if (message.startsWith('edit spider')) {
            editSpiderConfig();
        } else if (message.startsWith('update keyword mappings')) {
            updateKeywordMappings();
        } else if (message.startsWith('update spider rules')) {
            updateSpiderRules();
        } else {
            // Send the message to the server
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            }).then(response => response.json())
              .then(data => {
                  // Display the server's response in the chatbox
                  typeMessage(data.response, 'bot');
              }).catch(error => {
                  console.error('Fetch error:', error);
                  alert('There was an error sending the message to the server.');
              });
        }
    }
}

function addMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = text;

    const chatArea = document.getElementById('chat-area');
    chatArea.appendChild(messageElement);

    scrollToBottom();
}

function typeMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    const chatArea = document.getElementById('chat-area');
    chatArea.appendChild(messageElement);

    let index = 0;
    function typeNextCharacter() {
        if (index < text.length) {
            messageElement.textContent += text.charAt(index);
            index++;
            setTimeout(typeNextCharacter, 50); // Adjust typing speed here
        } else {
            scrollToBottom();
        }
    }
    typeNextCharacter();
}

function scrollToBottom() {
    const chatArea = document.getElementById('chat-area');
    setTimeout(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    }, 100);  // Small delay to ensure DOM is updated
}

function autoResizeTextarea(textarea) {
    textarea.style.height = '20px'; // Reset to initial height
    textarea.style.height = textarea.scrollHeight + 'px';
}

function initiateSpiderSetup() {
    spiderConfig = {
        urls: [],
        description: ""
    };
    displaySpiderConfig();
}

function displaySpiderConfig() {
    const chatbox = document.getElementById('chat-area');
    const configMessageDiv = document.createElement('div');
    configMessageDiv.className = 'message bot';
    configMessageDiv.innerHTML = `
        <div>Spider Configuration:</div>
        <div>URLs: ${spiderConfig.urls.join(', ')}</div>
        <div>Description: ${spiderConfig.description}</div>
        <button onclick="addSpiderUrl()">Add URL</button>
        <button onclick="editSpiderDescription()">Edit Description</button>
        <button onclick="confirmSpiderSetup()">Confirm Setup</button>
    `;
    chatbox.appendChild(configMessageDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
}

function addSpiderUrl() {
    const url = prompt("Enter the URL to scrape:");
    if (url) {
        spiderConfig.urls.push(url);
        displaySpiderConfig();
    }
}

function editSpiderDescription() {
    const description = prompt("Enter the description of specific info to target:");
    if (description) {
        spiderConfig.description = description;
        displaySpiderConfig();
    }
}

function confirmSpiderSetup() {
    if (spiderConfig.urls.length > 0 && spiderConfig.description) {
        fetch('/start_spider', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(spiderConfig)
        }).then(response => response.json())
          .then(data => {
              typeMessage('Spider started: ' + data.message, 'bot');
          }).catch(error => {
              console.error('Fetch error:', error);
              alert('There was an error starting the spider.');
          });
    } else {
        alert("Please add at least one URL and a description.");
    }
}

function stopSpider() {
    fetch('/stop_spider', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
      .then(data => {
          typeMessage('Spider stopped: ' + data.message, 'bot');
      }).catch(error => {
          console.error('Fetch error:', error);
          alert('There was an error stopping the spider.');
      });
}

function editSpiderConfig() {
    initiateSpiderSetup();
}

function updateKeywordMappings() {
    const newMappings = prompt("Enter new keyword mappings in JSON format:");
    if (newMappings) {
        fetch('/update_keyword_mappings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: newMappings
        }).then(response => response.json())
          .then(data => {
              typeMessage('Keyword mappings updated: ' + data.message, 'bot');
          }).catch(error => {
              console.error('Fetch error:', error);
              alert('There was an error updating keyword mappings.');
          });
    }
}

function updateSpiderRules() {
    const newRules = prompt("Enter new spider rules in JSON format:");
    if (newRules) {
        fetch('/update_spider_rules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: newRules
        }).then(response => response.json())
          .then(data => {
              typeMessage('Spider rules updated: ' + data.message, 'bot');
          }).catch(error => {
              console.error('Fetch error:', error);
              alert('There was an error updating spider rules.');
          });
    }
}
