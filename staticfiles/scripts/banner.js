const walletBalance = JSON.parse(document.getElementById('wallet_data').textContent);

if (walletBalance <= 0.5) {
    const banner = document.createElement('div');

    const dashboardTokens = document.querySelector('.dashboard-tokens');
    banner.style.width = '100%';
    banner.style.backgroundColor = 'red'; // You can customize the color
    banner.style.color = 'white';
    banner.style.textAlign = 'center';
    banner.style.padding = '10px';
    banner.style.borderRadius = '10px';
    banner.style.border = "3px outset black";
    banner.innerText = "App wallet BNB balance is too low. Contact us for replenishment. You can't place bets now.";
    
    const inputs = document.querySelectorAll('input');
    const buttons = document.querySelectorAll('button');
    inputs.forEach(input => {
        input.disabled = true;
    });
    buttons.forEach(button => {
        button.disabled = true;
    })
    console.log(dashboardTokens.appendChild(banner));
    dashboardTokens.appendChild(banner);
}
