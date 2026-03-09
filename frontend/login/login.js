
       const gridContainer = document.getElementById('gridContainer');

        for (let i = 0; i < 30; i++) {
            const line = document.createElement('div');
            line.className = 'grid-line';
            line.style.width = '100%';
            line.style.height = '1px';
            line.style.top = (i * 50) + 'px';
            line.style.animationDelay = (i * 0.1) + 's';
            gridContainer.appendChild(line);
        }

        for (let i = 0; i < 40; i++) {
            const line = document.createElement('div');
            line.className = 'grid-line';
            line.style.width = '1px';
            line.style.height = '100%';
            line.style.left = (i * 50) + 'px';
            line.style.animationDelay = (i * 0.1 + 0.5) + 's';
            gridContainer.appendChild(line);
        }

        const shapeCount = 5;
        for (let i = 0; i < shapeCount; i++) {
            const shape = document.createElement('div');
            shape.className = 'shape';
            const size = Math.random() * 200 + 100;
            shape.style.width = size + 'px';
            shape.style.height = size + 'px';
            shape.style.left = Math.random() * 100 + '%';
            shape.style.top = Math.random() * 100 + '%';
            shape.style.animationDelay = (i * 1.6) + 's';
            shape.style.animationDuration = (Math.random() * 4 + 6) + 's';
            gridContainer.appendChild(shape);
        }

        const togglePassword = document.getElementById('togglePassword');
        const passwordField = document.getElementById('passwordField');
        let isPasswordVisible = false;

        togglePassword.addEventListener('click', () => {
            isPasswordVisible = !isPasswordVisible;
            passwordField.type = isPasswordVisible ? 'text' : 'password';
            togglePassword.className = isPasswordVisible
                ? 'fa-solid fa-eye-slash toggle-icon'
                : 'fa-solid fa-eye toggle-icon';
        });

        document.getElementById("loginForm")
.addEventListener("submit", async (e) => {

    e.preventDefault();

    const username =
        document.getElementById("username").value;

    const password =
        document.getElementById("passwordField").value;

    const response = await fetch(
        "http://127.0.0.1:5000/login",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        }
    );

    const data = await response.json();

    if (response.ok) {
        localStorage.setItem("token", data.token);
        window.location.href = "../user_data.html";
    } else {
        alert(data.error);
    }
});
// Initialize Google once when page loads
window.onload = function(){

    google.accounts.id.initialize({
        client_id: "1023042512555-glcglt2t9ep0jmg21mrv505g488ho62h.apps.googleusercontent.com",
        callback: handleGoogleResponse
    });

};

// When user clicks Google button
document.getElementById("googleLogin")
.addEventListener("click", () => {

    google.accounts.id.prompt();

});


async function handleGoogleResponse(response){

    const token = response.credential;

    const res = await fetch(
        "http://127.0.0.1:5000/google-login",
        {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({token})
        }
    );

    const data = await res.json();

    if(res.ok){

        localStorage.setItem("token",data.token);

        window.location.href="../user_data.html";

    }else{
        alert("Google login failed");
    }
}
