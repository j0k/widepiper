// Flappy Bird Game
(function() {
    const canvas = document.getElementById('flappy-canvas');
    const ctx = canvas.getContext('2d');
    const overlay = document.getElementById('game-overlay');
    const startBtn = document.getElementById('start-btn');
    const overlayTitle = document.getElementById('overlay-title');
    const overlayScore = document.getElementById('overlay-score');
    const overlayEarned = document.getElementById('overlay-earned');
    const currentScoreEl = document.getElementById('current-score');
    const earnedAmountEl = document.getElementById('earned-amount');
    const gameBalanceEl = document.getElementById('game-balance');

    // Game constants
    const REWARD_PER_PIPE = 0.01;
    const GRAVITY = 0.5;
    const JUMP_FORCE = -8;
    const PIPE_SPEED = 3;
    const PIPE_GAP = 150;
    const PIPE_WIDTH = 60;
    const PIPE_SPAWN_INTERVAL = 1500;

    // Game state
    let gameRunning = false;
    let score = 0;
    let earnedThisGame = 0;
    let bird = null;
    let pipes = [];
    let lastPipeSpawn = 0;
    let animationId = null;

    // Resize canvas
    function resizeCanvas() {
        const wrapper = canvas.parentElement;
        canvas.width = wrapper.clientWidth;
        canvas.height = wrapper.clientHeight;
    }

    // Bird class
    class Bird {
        constructor() {
            this.x = canvas.width * 0.2;
            this.y = canvas.height / 2;
            this.width = 35;
            this.height = 25;
            this.velocity = 0;
            this.rotation = 0;
        }

        jump() {
            this.velocity = JUMP_FORCE;
        }

        update() {
            this.velocity += GRAVITY;
            this.y += this.velocity;
            this.rotation = Math.min(Math.max(this.velocity * 3, -30), 90);
        }

        draw() {
            ctx.save();
            ctx.translate(this.x + this.width / 2, this.y + this.height / 2);
            ctx.rotate(this.rotation * Math.PI / 180);
            
            // Body
            ctx.fillStyle = '#FFD700';
            ctx.beginPath();
            ctx.ellipse(0, 0, this.width / 2, this.height / 2, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#DAA520';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Wing
            ctx.fillStyle = '#FFA500';
            ctx.beginPath();
            ctx.ellipse(-5, 5, 10, 6, -0.3, 0, Math.PI * 2);
            ctx.fill();
            
            // Eye
            ctx.fillStyle = 'white';
            ctx.beginPath();
            ctx.arc(8, -5, 7, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = 'black';
            ctx.beginPath();
            ctx.arc(10, -5, 3, 0, Math.PI * 2);
            ctx.fill();
            
            // Beak
            ctx.fillStyle = '#FF6347';
            ctx.beginPath();
            ctx.moveTo(15, 0);
            ctx.lineTo(25, 3);
            ctx.lineTo(15, 6);
            ctx.closePath();
            ctx.fill();
            
            ctx.restore();
        }

        getBounds() {
            return {
                x: this.x + 5,
                y: this.y + 3,
                width: this.width - 10,
                height: this.height - 6
            };
        }
    }

    // Pipe class
    class Pipe {
        constructor() {
            this.x = canvas.width;
            this.gapY = Math.random() * (canvas.height - PIPE_GAP - 100) + 50;
            this.width = PIPE_WIDTH;
            this.passed = false;
        }

        update() {
            this.x -= PIPE_SPEED;
        }

        draw() {
            // Top pipe
            ctx.fillStyle = '#228B22';
            ctx.fillRect(this.x, 0, this.width, this.gapY);
            ctx.fillStyle = '#32CD32';
            ctx.fillRect(this.x - 5, this.gapY - 30, this.width + 10, 30);
            
            // Bottom pipe
            const bottomY = this.gapY + PIPE_GAP;
            ctx.fillStyle = '#228B22';
            ctx.fillRect(this.x, bottomY, this.width, canvas.height - bottomY);
            ctx.fillStyle = '#32CD32';
            ctx.fillRect(this.x - 5, bottomY, this.width + 10, 30);
            
            // Pipe borders
            ctx.strokeStyle = '#006400';
            ctx.lineWidth = 2;
            ctx.strokeRect(this.x, 0, this.width, this.gapY);
            ctx.strokeRect(this.x, bottomY, this.width, canvas.height - bottomY);
        }

        checkCollision(bird) {
            const b = bird.getBounds();
            const topPipe = { x: this.x, y: 0, width: this.width, height: this.gapY };
            const bottomPipe = { x: this.x, y: this.gapY + PIPE_GAP, width: this.width, height: canvas.height };
            
            return this.rectCollision(b, topPipe) || this.rectCollision(b, bottomPipe);
        }

        rectCollision(r1, r2) {
            return r1.x < r2.x + r2.width &&
                   r1.x + r1.width > r2.x &&
                   r1.y < r2.y + r2.height &&
                   r1.y + r1.height > r2.y;
        }
    }


    // Draw background
    function drawBackground() {
        // Sky gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, '#87CEEB');
        gradient.addColorStop(0.7, '#87CEEB');
        gradient.addColorStop(0.7, '#90EE90');
        gradient.addColorStop(1, '#228B22');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Clouds
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        drawCloud(50, 50, 40);
        drawCloud(150, 80, 30);
        drawCloud(250, 40, 35);
    }

    function drawCloud(x, y, size) {
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.arc(x + size * 0.8, y - size * 0.3, size * 0.7, 0, Math.PI * 2);
        ctx.arc(x + size * 1.5, y, size * 0.8, 0, Math.PI * 2);
        ctx.fill();
    }

    // Game loop
    function gameLoop(timestamp) {
        if (!gameRunning) return;

        // Clear and draw background
        drawBackground();

        // Spawn pipes
        if (timestamp - lastPipeSpawn > PIPE_SPAWN_INTERVAL) {
            pipes.push(new Pipe());
            lastPipeSpawn = timestamp;
        }

        // Update and draw pipes
        for (let i = pipes.length - 1; i >= 0; i--) {
            const pipe = pipes[i];
            pipe.update();
            pipe.draw();

            // Check if bird passed pipe
            if (!pipe.passed && pipe.x + pipe.width < bird.x) {
                pipe.passed = true;
                score++;
                earnedThisGame += REWARD_PER_PIPE;
                currentScoreEl.textContent = score;
                earnedAmountEl.textContent = earnedThisGame.toFixed(2);
            }

            // Remove off-screen pipes
            if (pipe.x + pipe.width < 0) {
                pipes.splice(i, 1);
            }

            // Check collision
            if (pipe.checkCollision(bird)) {
                gameOver();
                return;
            }
        }

        // Update and draw bird
        bird.update();
        bird.draw();

        // Check boundaries
        if (bird.y < 0 || bird.y + bird.height > canvas.height) {
            gameOver();
            return;
        }

        animationId = requestAnimationFrame(gameLoop);
    }

    // Start game
    function startGame() {
        resizeCanvas();
        bird = new Bird();
        pipes = [];
        score = 0;
        earnedThisGame = 0;
        lastPipeSpawn = 0;
        gameRunning = true;
        
        currentScoreEl.textContent = '0';
        earnedAmountEl.textContent = '0.00';
        overlay.classList.add('hidden');
        
        animationId = requestAnimationFrame(gameLoop);
    }

    // Game over
    function gameOver() {
        gameRunning = false;
        if (animationId) {
            cancelAnimationFrame(animationId);
        }

        overlayTitle.textContent = 'Game Over!';
        overlayScore.textContent = `Score: ${score}`;
        overlayEarned.textContent = `Earned: +${earnedThisGame.toFixed(2)} USDT`;
        startBtn.textContent = 'Play Again';
        overlay.classList.remove('hidden');

        // Save earnings to server
        if (earnedThisGame > 0) {
            saveEarnings(earnedThisGame);
        }
    }

    // Save earnings to server
    async function saveEarnings(amount) {
        try {
            const response = await fetch('/api/v1/games/earn/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ amount: amount })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.new_balance !== undefined) {
                    gameBalanceEl.textContent = parseFloat(data.new_balance).toFixed(2);
                }
            }
        } catch (error) {
            console.error('Failed to save earnings:', error);
        }
    }

    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Event listeners
    startBtn.addEventListener('click', startGame);

    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            if (gameRunning && bird) {
                bird.jump();
            } else if (!gameRunning) {
                startGame();
            }
        }
    });

    canvas.addEventListener('click', () => {
        if (gameRunning && bird) {
            bird.jump();
        }
    });

    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        if (gameRunning && bird) {
            bird.jump();
        }
    });

    // Handle resize
    window.addEventListener('resize', () => {
        if (!gameRunning) {
            resizeCanvas();
            drawBackground();
        }
    });

    // Initial setup
    resizeCanvas();
    drawBackground();
})();
