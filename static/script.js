document.addEventListener("DOMContentLoaded", () => {
    carregarLavagens();
});

let dadosLavagens = [];
let graficoFaturamento = null;

// ================= REGISTRAR LAVAGEM =================
async function registrarLavagem() {
    const form = {
        cliente: document.getElementById("cliente").value.trim(),
        marca: document.getElementById("marca").value,
        modelo: document.getElementById("modelo").value.trim(),
        placa: document.getElementById("placa").value.trim().toUpperCase(),
        tipo_lavagem: document.getElementById("tipo_lavagem").value,
        valor: parseFloat(document.getElementById("valor").value),
        status_pagamento: document.getElementById("status_pagamento").value,
        observacoes: document.getElementById("observacoes").value.trim()
    };

    if (!form.cliente || !form.marca || !form.modelo || !form.placa || isNaN(form.valor)) {
        alert("Por favor, preencha todos os campos obrigatorios.");
        return;
    }

    try {
        const response = await fetch("/api/lavagens", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(form)
        });

        if (response.ok) {
            alert("Lavagem registrada com sucesso!");
            limparFormulario();
            carregarLavagens();
        } else {
            const err = await response.json();
            alert(`Erro: ${err.erro}`);
        }
    } catch (error) {
        console.error("Erro ao registrar:", error);
        alert("Erro ao conectar com o servidor.");
    }
}

// ================= CARREGAR DADOS =================
async function carregarLavagens() {
    try {
        const response = await fetch("/api/lavagens");
        if (response.ok) {
            dadosLavagens = await response.json();
            atualizarInterface();
            renderizarGrafico();
        }
    } catch (error) {
        console.error("Erro ao carregar lavagens:", error);
    }
}

// ================= ATUALIZAR INTERFACE =================
function atualizarInterface() {
    const tabela = document.getElementById("tabela-corpo");
    tabela.innerHTML = "";
    let faturamentoTotal = 0;
    let faturamentoHoje = 0;
    let lavagensTotal = 0;
    let lavagensHoje = 0;

    // Obter a data de hoje no fuso horário local, formatada como YYYY-MM-DD
    const hoje = new Date();
    const hojeFormatado = hoje.getFullYear() + '-' +
                          String(hoje.getMonth() + 1).padStart(2, '0') + '-' +
                          String(hoje.getDate()).padStart(2, '0');

    dadosLavagens.forEach(item => {
        const valor = parseFloat(item.valor);

        // Extrair a parte da data do registro da lavagem (YYYY-MM-DD)
        const dataRegistroFormatada = item.data_registro.split(' ')[0];

        // Comparar as datas
        const isToday = dataRegistroFormatada === hojeFormatado;

        // Apenas soma o valor se o status_pagamento for 'Pago'
        if (item.status_pagamento === "Pago") {
            faturamentoTotal += valor;
            if (isToday) {
                faturamentoHoje += valor;
            }
        }

        // As contagens de lavagens (total e hoje) continuam a considerar todas as lavagens
        if (isToday) {
            lavagensHoje++;
        }
        lavagensTotal++;

        const linha = document.createElement("tr");
        const statusBadge = item.status_pagamento === "Pago" ? "badge-success" : "badge-warning";
        const acaoPagar = item.status_pagamento === "Pendente"
            ? `<button onclick="marcarPago(${item.id})" class="btn btn-sm btn-success" title="Marcar como Pago">✔</button>`
            : 
            '';
        linha.innerHTML = `
            <td>${item.id}</td>
            <td>${item.data_registro}</td>
            <td>${item.cliente}</td>
            <td>${item.marca} ${item.modelo}</td>
            <td>${item.placa}</td>
            <td>${item.tipo_lavagem}</td>
            <td>R$ ${valor.toFixed(2)}</td>
            <td><span class="badge ${statusBadge}">${item.status_pagamento}</span></td>
            <td class="action-btns">
                ${acaoPagar}
                <button onclick="excluirRegistro(${item.id})" class="btn btn-sm btn-danger" title="Excluir">🗑</button>
            </td>
        `;
        tabela.appendChild(linha);
    });

    document.getElementById("stat-lavagens-hoje").innerText = lavagensHoje;
    document.getElementById("stat-lavagens-total").innerText = lavagensTotal;
    document.getElementById("stat-faturamento-hoje").innerText = `R$ ${faturamentoHoje.toFixed(2)}`;
    document.getElementById("stat-faturamento-total").innerText = `R$ ${faturamentoTotal.toFixed(2)}`;
}

// ================= ACOES =================
async function marcarPago(id) {
    if (confirm("Deseja marcar esta lavagem como PAGA?")) {
        try {
            const response = await fetch(`/api/lavagens/${id}/pagar`, { method: "PUT" });
            if (response.ok) carregarLavagens();
        } catch (error) {
            console.error("Erro ao atualizar pagamento:", error);
        }
    }
}

async function excluirRegistro(id) {
    if (confirm("Deseja realmente excluir este registro?")) {
        try {
            const response = await fetch(`/api/lavagens/${id}`, { method: "DELETE" });
            if (response.ok) carregarLavagens();
        } catch (error) {
            console.error("Erro ao excluir:", error);
        }
    }
}

// ================= GRAFICO =================
function renderizarGrafico() {
    const ctx = document.getElementById("grafico-faturamento").getContext("2d");
    
    // Agrupar dados por dia
    const resumo = {};
    dadosLavagens.slice().reverse().forEach(item => {
        const dia = item.data_registro.split(" ")[0];
        if (!resumo[dia]) resumo[dia] = 0;
        resumo[dia] += parseFloat(item.valor);
    });

    const labels = Object.keys(resumo);
    const data = Object.values(resumo);

    if (graficoFaturamento) {
        graficoFaturamento.destroy();
    }

    graficoFaturamento = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Faturamento Diario (R$)',
                data: data,
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

// ================= UTILITARIOS =================
function limparFormulario() {
    document.getElementById("cliente").value = "";
    document.getElementById("marca").value = "";
    document.getElementById("modelo").value = "";
    document.getElementById("placa").value = "";
    document.getElementById("valor").value = "";
    document.getElementById("observacoes").value = "";
    document.getElementById("tipo_lavagem").value = "Simples";
    document.getElementById("status_pagamento").value = "Pendente";
}
