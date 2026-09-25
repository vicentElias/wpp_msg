const elements = {
    connectionIndicator: document.querySelector("#connectionIndicator"),
    connectionLabel: document.querySelector("#connectionLabel"),
    currentDate: document.querySelector("#currentDate"),
    totalContacts: document.querySelector("#totalContacts"),
    selectedCount: document.querySelector("#selectedCount"),
    contactSearch: document.querySelector("#contactSearch"),
    selectVisible: document.querySelector("#selectVisible"),
    visibleCount: document.querySelector("#visibleCount"),
    contactList: document.querySelector("#contactList"),
    clearSelection: document.querySelector("#clearSelection"),
    messageTemplate: document.querySelector("#messageTemplate"),
    previewRecipient: document.querySelector("#previewRecipient"),
    messagePreview: document.querySelector("#messagePreview"),
    intervalMin: document.querySelector("#intervalMin"),
    intervalMax: document.querySelector("#intervalMax"),
    loadWait: document.querySelector("#loadWait"),
    startSending: document.querySelector("#startSending"),
    progressPanel: document.querySelector("#progressPanel"),
    progressTitle: document.querySelector("#progressTitle"),
    progressCount: document.querySelector("#progressCount"),
    progressBar: document.querySelector("#progressBar"),
    progressDetail: document.querySelector("#progressDetail"),
    resultList: document.querySelector("#resultList"),
};

let contacts = [];
let selectedIds = new Set();
let isRunning = false;

function greetingAtCurrentTime() {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return "Bom dia";
    if (hour >= 12 && hour < 18) return "Boa tarde";
    return "Boa noite";
}

function formatMessage(name) {
    return elements.messageTemplate.value
        .replaceAll("{nome}", name)
        .replaceAll("{saudacao}", greetingAtCurrentTime());
}

function filteredContacts() {
    const query = elements.contactSearch.value.trim().toLocaleLowerCase("pt-BR");
    if (!query) return contacts;
    return contacts.filter((contact) =>
        `${contact.nome} ${contact.telefone}`.toLocaleLowerCase("pt-BR").includes(query),
    );
}

function renderContacts() {
    const visibleContacts = filteredContacts();
    elements.contactList.replaceChildren();
    elements.visibleCount.textContent = `${visibleContacts.length} exibidos`;
    elements.selectVisible.checked = visibleContacts.length > 0
        && visibleContacts.every((contact) => selectedIds.has(contact.id));

    if (visibleContacts.length === 0) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = contacts.length ? "Nenhum contato encontrado." : "Não foi possível carregar os contatos.";
        elements.contactList.append(empty);
        updateSummary();
        return;
    }

    const fragment = document.createDocumentFragment();
    for (const contact of visibleContacts) {
        const row = document.createElement("label");
        row.className = "contact-row";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selectedIds.has(contact.id);
        checkbox.disabled = isRunning;
        checkbox.setAttribute("aria-label", `Selecionar ${contact.nome}`);
        checkbox.addEventListener("change", () => {
            if (checkbox.checked) selectedIds.add(contact.id);
            else selectedIds.delete(contact.id);
            updateSummary();
            updatePreview();
            updateSendButton();
            updateSelectVisible();
        });

        const avatar = document.createElement("span");
        avatar.className = "contact-avatar";
        avatar.setAttribute("aria-hidden", "true");
        avatar.textContent = contact.nome.trim().charAt(0).toLocaleUpperCase("pt-BR") || "?";

        const copy = document.createElement("span");
        copy.className = "contact-copy";
        const name = document.createElement("span");
        name.className = "contact-name";
        name.textContent = contact.nome;
        const phone = document.createElement("span");
        phone.className = "contact-phone";
        phone.textContent = contact.telefone;
        copy.append(name, phone);
        row.append(checkbox, avatar, copy);
        fragment.append(row);
    }
    elements.contactList.append(fragment);
    updateSummary();
}

function updateSelectVisible() {
    const visibleContacts = filteredContacts();
    elements.selectVisible.checked = visibleContacts.length > 0
        && visibleContacts.every((contact) => selectedIds.has(contact.id));
}

function updateSummary() {
    elements.selectedCount.textContent = selectedIds.size.toLocaleString("pt-BR");
}

function updatePreview() {
    const firstSelected = contacts.find((contact) => selectedIds.has(contact.id));
    const name = firstSelected?.nome || "Seu contato";
    elements.previewRecipient.textContent = firstSelected?.nome || "Exemplo de mensagem";
    elements.messagePreview.textContent = formatMessage(name);
}

function updateSendButton() {
    elements.startSending.disabled = isRunning || selectedIds.size === 0;
    elements.startSending.querySelector("span").textContent = isRunning
        ? "Envio em andamento"
        : "Iniciar envio";
}

function setConnection(connected, label) {
    elements.connectionIndicator.classList.toggle("is-connected", connected);
    elements.connectionLabel.textContent = label;
}

function renderProgress(status) {
    elements.progressPanel.hidden = false;
    const total = status.total || 0;
    const processed = status.processed || 0;
    const percentage = total ? Math.min(100, (processed / total) * 100) : 0;
    elements.progressCount.textContent = `${processed} / ${total}`;
    elements.progressBar.style.width = `${percentage}%`;
    elements.progressTitle.textContent = status.running
        ? "Envio em andamento"
        : status.completed ? "Processo concluído" : "Envio preparado";

    if (status.current?.status === "enviando") {
        elements.progressDetail.textContent = `Abrindo conversa com ${status.current.nome}…`;
    } else if (status.running) {
        elements.progressDetail.textContent = "Aguardando o próximo contato…";
    } else if (status.error) {
        elements.progressDetail.textContent = status.error;
    } else if (status.completed) {
        elements.progressDetail.textContent = "Todos os contatos selecionados foram processados.";
    }

    elements.resultList.replaceChildren();
    for (const result of (status.results || []).slice(-8)) {
        const item = document.createElement("li");
        if (result.status === "erro") item.classList.add("is-error");
        const name = document.createElement("span");
        name.textContent = result.nome;
        const outcome = document.createElement("span");
        outcome.textContent = result.status === "erro" ? "Falha" : "Concluído";
        item.append(name, outcome);
        elements.resultList.append(item);
    }
}

async function loadContacts() {
    try {
        const [contactsResponse, statusResponse] = await Promise.all([
            fetch("/api/contacts"),
            fetch("/api/status"),
        ]);
        if (!contactsResponse.ok || !statusResponse.ok) throw new Error("Falha ao consultar a aplicação.");
        const data = await contactsResponse.json();
        contacts = data.contacts;
        elements.totalContacts.textContent = data.total.toLocaleString("pt-BR");
        setConnection(true, "Aplicação conectada");
        elements.currentDate.textContent = new Intl.DateTimeFormat("pt-BR", {
            weekday: "long", day: "numeric", month: "long", year: "numeric",
        }).format(new Date());
        renderContacts();
        updatePreview();
        updateSendButton();
        applyStatus(await statusResponse.json());
    } catch (error) {
        setConnection(false, "Aplicação indisponível");
        elements.contactList.innerHTML = "";
        const message = document.createElement("div");
        message.className = "empty-state";
        message.textContent = "Inicie a aplicação Python para carregar os contatos.";
        elements.contactList.append(message);
        elements.visibleCount.textContent = "";
    }
}

function applyStatus(status) {
    const runningStateChanged = isRunning !== status.running;
    isRunning = status.running;
    updateSendButton();
    if (status.running || status.completed || status.error) renderProgress(status);
    if (runningStateChanged) renderContacts();
}

async function pollStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) return;
        setConnection(true, "Aplicação conectada");
        applyStatus(await response.json());
    } catch {
        setConnection(false, "Conexão interrompida");
    }
}

async function startSending() {
    if (!selectedIds.size || isRunning) return;
    const total = selectedIds.size;
    const accepted = window.confirm(
        `Iniciar o envio para ${total} ${total === 1 ? "contato" : "contatos"}? O WhatsApp Web será aberto no navegador.`,
    );
    if (!accepted) return;

    try {
        const response = await fetch("/api/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                indices: [...selectedIds],
                texto_padrao: elements.messageTemplate.value,
                intervalo_minimo: Number(elements.intervalMin.value),
                intervalo_maximo: Number(elements.intervalMax.value),
                tempo_de_espera: Number(elements.loadWait.value),
            }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Não foi possível iniciar o envio.");
        applyStatus(result.status);
    } catch (error) {
        window.alert(error.message);
    }
}

elements.contactSearch.addEventListener("input", renderContacts);
elements.messageTemplate.addEventListener("input", updatePreview);
elements.startSending.addEventListener("click", startSending);
elements.selectVisible.addEventListener("change", () => {
    for (const contact of filteredContacts()) {
        if (elements.selectVisible.checked) selectedIds.add(contact.id);
        else selectedIds.delete(contact.id);
    }
    renderContacts();
    updatePreview();
    updateSendButton();
});
elements.clearSelection.addEventListener("click", () => {
    selectedIds.clear();
    renderContacts();
    updatePreview();
    updateSendButton();
});
document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        event.preventDefault();
        elements.contactSearch.focus();
    }
});

loadContacts();
window.setInterval(pollStatus, 1200);