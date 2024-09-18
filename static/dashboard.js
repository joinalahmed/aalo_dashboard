document.addEventListener('DOMContentLoaded', function() {
    showDashboard();
    document.getElementById('createProjectForm').addEventListener('submit', createProject);
    document.getElementById('createApplicationForm').addEventListener('submit', createApplication);
});

function showDashboard() {
    document.getElementById('contentTitle').innerText = 'Dashboard';
    
    fetch('/api/get_dashboard_data')
        .then(response => response.json())
        .then(data => {
            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = `
                <div class="card-grid">
                    <div class="card">
                        <h3>API Usage</h3>
                        <p>Total Requests: ${data.total_requests}</p>
                        <p>This Month: ${data.requests_this_month}</p>
                        <canvas id="apiUsageChart"></canvas>
                    </div>
                    <div class="card">
                        <h3>Projects</h3>
                        <p>Total Projects: ${data.total_projects}</p>
                        <button onclick="showProjects()">View All Projects</button>
                    </div>
                    <div class="card">
                        <h3>Applications</h3>
                        <p>Total Applications: ${data.total_applications}</p>
                        <button onclick="showApplications()">View All Applications</button>
                    </div>
                    <div class="card">
                        <h3>API Keys</h3>
                        <p>Active API Keys: ${data.active_api_keys}</p>
                        <button onclick="showApiKeys()">Manage API Keys</button>
                    </div>
                </div>
            `;

            const ctx = document.getElementById('apiUsageChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.usage_data.map(d => d.date),
                    datasets: [{
                        label: 'API Requests',
                        data: data.usage_data.map(d => d.requests),
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            document.getElementById('contentArea').innerHTML = '<p>Error loading dashboard data. Please try again later.</p>';
        });
}

function showProjects() {
    const contentTitleContainer = document.getElementById('contentTitle');
    contentTitleContainer.innerHTML = '';
    const title = document.createElement('h2');
    title.innerText = 'Projects';
    const button = document.createElement('button');
    button.innerText = 'Create';
    button.onclick = () => showModal('projectModal');
    contentTitleContainer.appendChild(title);
    contentTitleContainer.appendChild(button);

    fetch('/api/get_projects')
        .then(response => response.json())
        .then(projects => {
            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = `<div class="card-grid" id="projectCards"></div>`;
            const projectCards = document.getElementById('projectCards');

            projects.forEach(project => {
                const projectCard = document.createElement('div');
                projectCard.className = 'card';
                projectCard.innerHTML = `
                    <h3>${project.name}</h3>
                    <p>${project.description || 'No description'}</p>
                    <button onclick="loadProjectDetails('${project.id}')">View Details</button>
                `;
                projectCards.appendChild(projectCard);
            });
        })
        .catch(error => console.error('Error:', error));
}

function loadProjectDetails(projectId) {
    fetch(`/api/get_project/${projectId}`)
        .then(response => response.json())
        .then(project => {
            const contentTitleContainer = document.getElementById('contentTitle');
            contentTitleContainer.innerHTML = '';
            const title = document.createElement('h2');
            title.innerText = project.name;
            const button = document.createElement('button');
            button.innerText = 'Create';
            button.onclick = () => showApplicationModal(project.id);
            contentTitleContainer.appendChild(title);
            contentTitleContainer.appendChild(button);

            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = `
                <h3>Applications</h3>
                <div id="applicationCards" class="card-grid"></div>
            `;
            
            loadProjectApplications(projectId);
        })
        .catch(error => console.error('Error:', error));
}

function loadProjectApplications(projectId) {
    fetch(`/api/get_applications/${projectId}`)
        .then(response => response.json())
        .then(applications => {
            const applicationCards = document.getElementById('applicationCards');
            applicationCards.innerHTML = '';
            applications.forEach(app => {
                const appCard = document.createElement('div');
                appCard.className = 'card';
                appCard.innerHTML = `
                    <h3>${app.name}</h3>
                    <p>${app.description || 'No description'}</p>
                    <button onclick="loadApplicationDetails('${app.id}')">View Details</button>
                `;
                applicationCards.appendChild(appCard);
            });
        })
        .catch(error => console.error('Error:', error));
}

function showApplications() {
    document.getElementById('contentTitle').innerText = 'Applications';
    
    fetch('/api/get_projects')
        .then(response => response.json())
        .then(projects => {
            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = '<div class="card-grid" id="allApplicationCards"></div>';
            const allApplicationCards = document.getElementById('allApplicationCards');

            projects.forEach(project => {
                fetch(`/api/get_applications/${project.id}`)
                    .then(response => response.json())
                    .then(applications => {
                        applications.forEach(app => {
                            const appCard = document.createElement('div');
                            appCard.className = 'card';
                            appCard.innerHTML = `
                                <h3>${app.name}</h3>
                                <p>Project: ${project.name}</p>
                                <p>${app.description || 'No description'}</p>
                                <button onclick="loadApplicationDetails('${app.id}')">View Details</button>
                            `;
                            allApplicationCards.appendChild(appCard);
                        });
                    })
                    .catch(error => console.error('Error:', error));
            });
        })
        .catch(error => console.error('Error:', error));
}

function loadApplicationDetails(appId) {
    fetch(`/api/get_application/${appId}`)
        .then(response => response.json())
        .then(app => {
            const contentTitleContainer = document.getElementById('contentTitle');
            contentTitleContainer.innerHTML = '';
            const title = document.createElement('h2');
            title.innerText = app.name;
            const button = document.createElement('button');
            button.innerText = 'Manage API Keys';
            button.onclick = () => showApiKeyModal(app.id);
            contentTitleContainer.appendChild(title);
            contentTitleContainer.appendChild(button);

            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = `
                <div class="application-details" data-app-id="${app.id}">
                    <div class="card api-traces">
                        <h3>API Traces</h3>
                        <div class="api-traces-content">
                            <div class="json-file-list">
                                <h4>JSON Files</h4>
                                <div id="jsonFileList"></div>
                            </div>
                            <div class="json-content">
                                <h4>JSON Content</h4>
                                <div id="jsonContent"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            loadJsonFiles(app.id);
        })
        .catch(error => console.error('Error:', error));
}

function loadJsonFiles(appId) {
    fetch(`/api/get_json_files/${appId}`)
        .then(response => response.json())
        .then(files => {
            const jsonFileList = document.getElementById('jsonFileList');
            if (Object.keys(files).length === 0) {
                jsonFileList.innerHTML = `
                    <p>No API traces available</p>
                    <p>Here's an example of how to push JSON data using Python:</p>
                    <div class="code-block">
                        <pre><code class="language-python">
import requests
import json

url = '&lt;endpoint&gt;/api/store_json'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer APPLICATION_KEY'
}
data = {
    "data": {
        'key1': 'value1',
        'key2': 'value2'
    },
    "runID": "iwudjkfdd"
}

response = requests.post(url, headers=headers, data=json.dumps(data))

if response.status_code == 200:
    print('JSON stored successfully')
    print(response.json())
else:
    print('Error:', response.json())
                        </code></pre>
                        <button class="copy-btn" onclick="copyCode(this)">📋</button>
                    </div>
                    <p>Replace &lt;endpoint&gt; with your API endpoint and APPLICATION_KEY with your actual API key.</p>
                `;
            } else {
                jsonFileList.innerHTML = renderFileTree(files);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const jsonFileList = document.getElementById('jsonFileList');
            jsonFileList.innerHTML = '<p>Error loading API traces. Please try again later.</p>';
        });
}

function renderFileTree(tree, path = '') {
    let html = '<ul>';
    for (const [key, value] of Object.entries(tree)) {
        if (typeof value === 'object') {
            html += `<li><span class="caret">${key}</span>${renderFileTree(value, path + key + '/')}</li>`;
        } else {
            html += `<li><a href="#" onclick="loadJsonContent('${value}')">${key}</a></li>`;
        }
    }
    html += '</ul>';
    return html;
}

function loadJsonContent(filePath) {
    fetch(`/api/get_json_content/${encodeURIComponent(filePath)}`)
        .then(response => response.json())
        .then(content => {
            const jsonContent = document.getElementById('jsonContent');
            const preElement = document.createElement('pre');
            preElement.className = 'json-viewer';
            preElement.textContent = JSON.stringify(content, null, 2);
            jsonContent.innerHTML = '';
            jsonContent.appendChild(preElement);
        })
        .catch(error => {
            console.error('Error:', error);
            const jsonContent = document.getElementById('jsonContent');
            jsonContent.innerHTML = '<p>Error loading JSON content. Please try again later.</p>';
        });
}

function showApiKeyModal(appId) {
    const modal = document.getElementById('apiKeyModal');
    modal.style.display = 'block';
    loadApiKeys(appId);
}

function loadApiKeys(appId) {
    fetch(`/api/get_api_keys/${appId}`)
        .then(response => response.json())
        .then(keys => {
            const apiKeyList = document.getElementById('apiKeyList');
            apiKeyList.innerHTML = '';
            keys.forEach(key => {
                const keyItem = document.createElement('div');
                keyItem.className = 'api-key-item';
                keyItem.innerHTML = `
                    <p>
                        API Key: 
                        <span class="api-key">${key.key}</span>
                        <button class="copy-btn" onclick="copyApiKey(this)">📋</button>
                    </p>
                    <p>Created: ${new Date(key.created_at).toLocaleString()}</p>
                    <p>Last Used: ${key.last_used ? new Date(key.last_used).toLocaleString() : 'Never'}</p>
                    <p>Status: ${key.is_active ? 'Active' : 'Revoked'}</p>
                    <button onclick="showApiKeyUsage('${key.id}')">View Usage</button>
                    <button onclick="revokeApiKey('${key.id}')" ${key.is_active ? '' : 'disabled'}>Revoke</button>
                    <button class="delete-btn" onclick="deleteApiKey('${key.id}')">Delete</button>
                `;
                apiKeyList.appendChild(keyItem);
            });
            document.getElementById('apiKeyList').style.display = 'block';
            document.getElementById('apiKeyUsage').style.display = 'none';
            document.getElementById('createApiKeyBtn').style.display = 'block';
        })
        .catch(error => console.error('Error:', error));
}

function showApiKeyUsage(keyId) {
    fetch(`/api/get_api_key_usage/${keyId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('apiKeyList').style.display = 'none';
            document.getElementById('apiKeyUsage').style.display = 'block';
            document.getElementById('createApiKeyBtn').style.display = 'none';
            
            const ctx = document.getElementById('apiKeyUsageChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.date),
                    datasets: [{
                        label: 'API Key Usage',
                        data: data.map(d => d.count),
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Error:', error));
}

function createApiKey() {
    const appId = document.querySelector('.application-details').dataset.appId;
    fetch(`/api/create_api_key/${appId}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            alert(`New API key created: ${data.api_key}`);
            loadApiKeys(appId);
        })
        .catch(error => console.error('Error:', error));
}

function revokeApiKey(keyId) {
    if (confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
        fetch(`/api/revoke_api_key/${keyId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.alert(data.error));
                } else {
                    alert('API key revoked successfully');
                    const appId = document.querySelector('.application-details').dataset.appId;
                    loadApiKeys(appId);
                }
            })
            .catch(error => console.error('Error:', error));
    }
}

function deleteApiKey(keyId) {
    if (confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
        fetch(`/api/delete_api_key/${keyId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    alert('API key deleted successfully');
                    const appId = document.querySelector('.application-details').dataset.appId;
                    loadApiKeys(appId);
                }
            })
            .catch(error => console.error('Error:', error));
    }
}

function createProject(e) {
    e.preventDefault();
    const name = document.getElementById('projectName').value;
    const description = document.getElementById('projectDescription').value;

    fetch('/api/create_project', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: name, description: description }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert('Project created successfully');
            closeModal('projectModal');
            showProjects();
        }
    })
    .catch(error => console.error('Error:', error));
}

function createApplication(e) {
    e.preventDefault();
    const projectId = document.getElementById('projectId').value;
    const name = document.getElementById('applicationName').value;
    const description = document.getElementById('applicationDescription').value;

    fetch('/api/create_application', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ project_id: projectId, name: name, description: description }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Error creating application:', data.error);
            alert(`Error creating application: ${data.error}`);
        } else {
            alert(`Application created successfully. Initial API Key: ${data.api_key}`);
            closeModal('applicationModal');
            loadProjectDetails(projectId);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while creating the application. Please try again.');
    });
}

function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showApplicationModal(projectId) {
    const modalContent = document.querySelector('#applicationModal .modal-content');
    let projectIdInput = document.getElementById('projectId');
    
    if (!projectIdInput) {
        projectIdInput = document.createElement('input');
        projectIdInput.type = 'hidden';
        projectIdInput.id = 'projectId';
        projectIdInput.name = 'projectId';
        modalContent.insertBefore(projectIdInput, modalContent.firstChild);
    }
    
    projectIdInput.value = projectId;
    showModal('applicationModal');
}

function copyCode(button) {
    const codeElement = button.closest('.code-block').querySelector('code');
    const codeText = codeElement.textContent;
    navigator.clipboard.writeText(codeText).then(() => {
        button.textContent = '✅';
        setTimeout(() => {
            button.textContent = '📋';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code: ', err);
        button.textContent = '❌';
        setTimeout(() => {
            button.textContent = '📋';
        }, 2000);
    });
}

function copyApiKey(button) {
    const apiKeyElement = button.previousElementSibling;
    const apiKey = apiKeyElement.textContent;
    navigator.clipboard.writeText(apiKey).then(() => {
        button.textContent = '✅';
        setTimeout(() => {
            button.textContent = '📋';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy API Key: ', err);
        button.textContent = '❌';
        setTimeout(() => {
            button.textContent = '📋';
        }, 2000);
    });
}

function showApiDocs() {
    document.getElementById('contentTitle').innerText = 'API Documentation';
    document.getElementById('contentArea').innerHTML = `
    <h1>Aalo Labs API Documentation</h1>

    <h3>Authenticate API Key</h3>
    <ul>
        <li><strong>URL</strong>: /api/authenticate_key</li>
        <li><strong>Method</strong>: POST</li>
        <li><strong>Headers</strong>:
            <ul>
                <li><strong>Authorization</strong>: Bearer <code>your_api_key_string</code></li>
                <li><strong>Content-Type</strong>: application/json</li>
            </ul>
        </li>
        <li><strong>Body</strong>:
            <pre><code>{}</code></pre>
            <p>(No body needed)</p>
        </li>
        <li><strong>Success Response</strong>:
            <ul>
                <li>Code: 200</li>
                <li>Content:
                    <pre><code>{
  "message": "API key authenticated successfully",
  "organization_id": "org_id",
  "organization_name": "Org Name",
  "project_id": "project_id",
  "project_name": "Project Name",
  "application_id": "app_id",
  "application_name": "App Name"
}</code></pre>
                </li>
            </ul>
        </li>
        <li><strong>Error Response</strong>:
            <ul>
                <li>Code: 401</li>
                <li>Content: <code>{ "error": "Invalid or inactive API key" }</code></li>
            </ul>
        </li>
    </ul>

    <h3>Store JSON Data</h3>
    <ul>
        <li><strong>URL</strong>: /api/store_json</li>
        <li><strong>Method</strong>: POST</li>
        <li><strong>Headers</strong>:
            <ul>
                <li><strong>Authorization</strong>: Bearer <code>your_api_key_string</code></li>
                <li><strong>Content-Type</strong>: application/json</li>
            </ul>
        </li>
        <li><strong>Body</strong>:
            <pre><code>{
  "data": {
    // Your JSON data here
  },
  "runID": "unique_run_identifier"
}</code></pre>
        </li>
        <li><strong>Success Response</strong>:
            <ul>
                <li>Code: 200</li>
                <li>Content:
                    <pre><code>{
  "message": "JSON data stored successfully",
  "file_path": "path/to/stored/file.json"
}</code></pre>
                </li>
            </ul>
        </li>
        <li><strong>Error Response</strong>:
            <ul>
                <li>Code: 401</li>
                <li>Content: <code>{ "error": "Invalid or inactive API key" }</code></li>
            </ul>
        </li>
    </ul>
    `;
}

// Event listener for caret clicks in JSON viewer
document.addEventListener('click', function(e) {
    if (e.target.className === 'caret') {
        e.target.parentElement.querySelector(".nested").classList.toggle("active");
        e.target.classList.toggle("caret-down");
    }
});

// Close modal if clicked outside of it
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = "none";
    }
}

// Initialize tooltips
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseover', showTooltip);
        tooltip.addEventListener('mouseout', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltipText = this.getAttribute('data-tooltip');
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    document.body.appendChild(tooltip);
    
    const rect = this.getBoundingClientRect();
    tooltip.style.top = `${rect.bottom + 5}px`;
    tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
}

function hideTooltip() {
    const tooltip = document.querySelector('.tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Call initTooltips when the page loads
document.addEventListener('DOMContentLoaded', initTooltips);
