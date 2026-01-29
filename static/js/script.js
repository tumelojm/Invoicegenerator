// Set today's date as default
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('issue_date').value = today;
    
    // Set due date to 14 days from now
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 14);
    document.getElementById('due_date').value = dueDate.toISOString().split('T')[0];
    
    // Add auto-calculation on input
    document.getElementById('servicesContainer').addEventListener('input', function(e) {
        if (e.target.classList.contains('service-quantity') || 
            e.target.classList.contains('service-price') || 
            e.target.classList.contains('service-tax')) {
            calculateTotals();
        }
    });
});

function addService() {
    const container = document.getElementById('servicesContainer');
    const serviceItem = document.querySelector('.service-item').cloneNode(true);
    
    // Clear all inputs in the cloned item
    serviceItem.querySelectorAll('input, textarea').forEach(input => {
        if (input.type === 'number' && input.classList.contains('service-quantity')) {
            input.value = '1';
        } else if (input.type === 'number' && input.classList.contains('service-tax')) {
            input.value = '0';
        } else {
            input.value = '';
        }
    });
    
    container.appendChild(serviceItem);
}

function removeService(button) {
    const container = document.getElementById('servicesContainer');
    const items = container.querySelectorAll('.service-item');
    
    if (items.length > 1) {
        button.closest('.service-item').remove();
        calculateTotals();
    } else {
        alert('You must have at least one service item.');
    }
}

function calculateTotals() {
    const serviceItems = document.querySelectorAll('.service-item');
    let subtotal = 0;
    let totalTax = 0;
    
    serviceItems.forEach(item => {
        const quantity = parseFloat(item.querySelector('.service-quantity').value) || 0;
        const price = parseFloat(item.querySelector('.service-price').value) || 0;
        const tax = parseFloat(item.querySelector('.service-tax').value) || 0;
        
        subtotal += (quantity * price);
        totalTax += tax;
    });
    
    const total = subtotal + totalTax;
    
    document.getElementById('displaySubtotal').textContent = `R ${subtotal.toFixed(2)}`;
    document.getElementById('displayTax').textContent = `R ${totalTax.toFixed(2)}`;
    document.getElementById('displayTotal').textContent = `R ${total.toFixed(2)}`;
    
    return { subtotal, totalTax, total };
}

document.getElementById('invoiceForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const messageDiv = document.getElementById('message');
    messageDiv.style.display = 'none';
    
    // Calculate totals
    const totals = calculateTotals();
    
    // Collect services data
    const services = [];
    document.querySelectorAll('.service-item').forEach(item => {
        const name = item.querySelector('.service-name').value;
        const quantity = parseFloat(item.querySelector('.service-quantity').value) || 0;
        const price = parseFloat(item.querySelector('.service-price').value) || 0;
        const tax = parseFloat(item.querySelector('.service-tax').value) || 0;
        const description = item.querySelector('.service-description').value;
        
        if (name) {
            services.push({
                name: name,
                quantity: quantity,
                unit_price: price,
                tax: tax,
                total: (quantity * price) + tax,
                description: description
            });
        }
    });
    
    // Prepare data
    const formData = {
        invoice_number: document.getElementById('invoice_number').value,
        issue_date: document.getElementById('issue_date').value,
        due_date: document.getElementById('due_date').value,
        from_details: document.getElementById('from_details').value,
        to_details: document.getElementById('to_details').value,
        services: services,
        bank_details: document.getElementById('bank_details').value,
        subtotal: totals.subtotal,
        tax: totals.totalTax,
        total: totals.total
    };
    
    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            messageDiv.className = 'message success';
            messageDiv.innerHTML = `
                ✅ Invoice generated successfully!
                <br>
                <a href="/download/${result.filename}" class="download-link">📥 Download Invoice</a>
            `;
            messageDiv.style.display = 'block';
            
            // Scroll to message
            messageDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            throw new Error(result.error || 'Failed to generate invoice');
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = `❌ Error: ${error.message}`;
        messageDiv.style.display = 'block';
        messageDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});