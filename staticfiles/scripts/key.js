const addressSpan = document.getElementById('key');
const maskSpan = document.getElementById('key').textContent;


addressSpan.addEventListener('click', () => {
  const myVariable = JSON.parse(document.getElementById('key_data').textContent);
  const fullAddress = myVariable;
  console.log(addressSpan.textContent)
  navigator.clipboard.writeText(fullAddress);
  addressSpan.textContent = "Copied";
  setTimeout(function() {
    addressSpan.textContent = fullAddress
    setTimeout(function() {
      addressSpan.textContent = maskSpan
      }, 10000);
    }, 500);

});


