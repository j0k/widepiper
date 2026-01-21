const addressSpan = document.getElementById('address');
const oldSpan = document.getElementById('address').textContent;

addressSpan.addEventListener('click', () => {
  const fullAddress = addressSpan.getAttribute('data-full-address');
  navigator.clipboard.writeText(fullAddress);
  addressSpan.textContent = "Copied";
  setTimeout(function() {
    addressSpan.textContent = oldSpan
    }, 500);
});