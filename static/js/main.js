// Utility Functions for Main Interface
console.log("Main JS Loaded Successfully");

// Fungsi untuk memperbarui panel informasi di Sidebar
function updateSidebarSummary(totalRegions, highRiskCount) {
    const summaryContainer = document.getElementById('summary-content');
    if (summaryContainer) {
        summaryContainer.innerHTML = `
            <div class="card p-2 mb-2">
                <small>Total Wilayah Terdeteksi</small>
                <strong>${totalRegions} Wilayah</strong>
            </div>
            <div class="card p-2 text-danger">
                <small>Wilayah Status AWAS/SIAGA</small>
                <strong>${highRiskCount} Wilayah</strong>
            </div>
        `;
    }
}

// Fungsi pembantu konversi warna hex ke label risiko
function getRiskBadgeClass(color) {
    switch (color) {
        case '#FF0000': return 'bg-danger';
        case '#FFA500': return 'bg-warning text-dark';
        case '#FFFF00': return 'bg-warning text-dark';
        default: return 'bg-success';
    }
}