document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const createAccountLink = document.getElementById('createAccountLink');
    const modal = document.getElementById('registerModal');
    const closeBtn = document.getElementsByClassName('close')[0];

    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        login(email, password);
    });

    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const orgName = document.getElementById('regOrgName').value;
        const email = document.getElementById('regEmail').value;
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('regConfirmPassword').value;
        
        if (password !== confirmPassword) {
            alert("Passwords do not match");
            return;
        }
        
        register(orgName, email, password);
    });

    createAccountLink.onclick = function() {
        modal.style.display = "block";
    }

    closeBtn.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    function login(email, password) {
        fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email, password: password }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                window.location.href = '/dashboard';
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred during login');
        });
    }

    function register(orgName, email, password) {
        fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ org_name: orgName, email: email, password: password }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('Registration successful. You can now log in.');
                modal.style.display = "none";
                // Clear the form
                registerForm.reset();
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred during registration');
        });
    }
});
