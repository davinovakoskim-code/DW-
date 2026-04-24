const listaChamados = document.querySelector("#lista-chamados");
const detalheChamado = document.querySelector("#detalhe-chamado");
const formValidacao = document.querySelector("#form-validacao");
const btnAnalisar = document.querySelector("#btn-analisar");
const btnImportarJira = document.querySelector("#btn-importar-jira");
const btnRecarregar = document.querySelector("#btn-recarregar");
const sugestaoBox = document.querySelector("#sugestao-box");
const validacoesBox = document.querySelector("#validacoes-box");
const listaValidacoes = document.querySelector("#lista-validacoes");
const resultadoImportacao = document.querySelector("#resultado-importacao");
const toast = document.querySelector("#toast");

let chamados = [];
let chamadoSelecionado = null;
let sugestaoAtual = null;

function mostrarMensagem(texto) {
  toast.textContent = texto;
  toast.classList.remove("hidden");
  window.setTimeout(() => toast.classList.add("hidden"), 3600);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const erro = await response.json().catch(() => ({}));
    throw new Error(erro.detail || "Erro ao chamar a API");
  }

  return response.json();
}

async function carregarChamados() {
  chamados = await requestJson("/chamados");
  renderizarLista();
}

function renderizarLista() {
  if (chamados.length === 0) {
    listaChamados.innerHTML = `
      <div class="empty-state">
        Nenhum chamado importado. Use o botao de importacao do Jira.
      </div>
    `;
    return;
  }

  listaChamados.innerHTML = chamados
    .map((chamado) => {
      const ativo = chamadoSelecionado && chamadoSelecionado.id === chamado.id ? "active" : "";
      return `
        <button class="ticket-item ${ativo}" type="button" data-id="${chamado.id}">
          <span class="ticket-title">${escapeHtml(chamado.chave_jira)} - ${escapeHtml(chamado.titulo_original)}</span>
          <span class="ticket-meta">
            <span>${escapeHtml(chamado.email_solicitante)}</span>
            <span class="status ${escapeHtml(chamado.status)}">${escapeHtml(chamado.status)}</span>
          </span>
        </button>
      `;
    })
    .join("");

  document.querySelectorAll(".ticket-item").forEach((item) => {
    item.addEventListener("click", () => selecionarChamado(Number(item.dataset.id)));
  });
}

async function importarChamadosDoJira() {
  btnImportarJira.disabled = true;
  btnImportarJira.textContent = "Importando...";
  resultadoImportacao.classList.add("hidden");

  try {
    const resultado = await requestJson("/jira/importar-chamados", { method: "POST" });
    resultadoImportacao.classList.remove("hidden");
    resultadoImportacao.innerHTML = `
      <strong>${escapeHtml(resultado.mensagem)}</strong>
      <span>Total encontrado: ${resultado.total_encontrados}</span>
      <span>Novos: ${resultado.importados}</span>
      <span>Atualizados: ${resultado.atualizados}</span>
      <span>Campo de organizacao: ${escapeHtml(resultado.campo_organizacao_usado)}</span>
    `;
    mostrarMensagem("Importacao concluida.");
    await carregarChamados();
  } catch (error) {
    mostrarMensagem(error.message);
  } finally {
    btnImportarJira.disabled = false;
    btnImportarJira.textContent = "Importar chamados do Jira";
  }
}

async function selecionarChamado(id) {
  chamadoSelecionado = await requestJson(`/chamados/${id}`);
  sugestaoAtual = obterUltimaSugestao(chamadoSelecionado);

  btnAnalisar.disabled = false;
  renderizarLista();
  renderizarDetalhe();
  renderizarSugestao();
  renderizarValidacoes();
}

function renderizarDetalhe() {
  detalheChamado.className = "detail-card";
  detalheChamado.innerHTML = `
    <strong>${escapeHtml(chamadoSelecionado.chave_jira)} - ${escapeHtml(chamadoSelecionado.titulo_original)}</strong>
    <span><b>Usuario:</b> ${escapeHtml(chamadoSelecionado.usuario_id)}</span>
    <span><b>E-mail:</b> ${escapeHtml(chamadoSelecionado.email_solicitante)}</span>
    <span><b>Organizacao atual:</b> ${escapeHtml(chamadoSelecionado.organizacao_atual || "Nao informada")}</span>
    <span><b>Status:</b> <span class="status ${escapeHtml(chamadoSelecionado.status)}">${escapeHtml(chamadoSelecionado.status)}</span></span>
    <div class="description">${escapeHtml(chamadoSelecionado.descricao)}</div>
  `;
}

function renderizarSugestao() {
  if (!sugestaoAtual) {
    sugestaoBox.classList.add("hidden");
    formValidacao.classList.add("hidden");
    return;
  }

  sugestaoBox.classList.remove("hidden");
  formValidacao.classList.remove("hidden");

  document.querySelector("#sug-organizacao").textContent = sugestaoAtual.organizacao_sugerida;
  document.querySelector("#sug-titulo").textContent = sugestaoAtual.titulo_sugerido;
  document.querySelector("#sug-categoria").textContent = sugestaoAtual.categoria_sugerida;
  document.querySelector("#sug-prioridade").textContent = sugestaoAtual.prioridade_sugerida;
  document.querySelector("#sug-confianca").textContent = `${Math.round(sugestaoAtual.confianca * 100)}%`;
  document.querySelector("#sug-solucao").textContent = sugestaoAtual.solucao_sugerida;
  document.querySelector("#sug-fontes").innerHTML = (sugestaoAtual.fontes_internas_usadas || [])
    .map((fonte) => `<li>${escapeHtml(fonte)}</li>`)
    .join("");
  document.querySelector("#sug-justificativa").textContent = sugestaoAtual.justificativa;

  formValidacao.elements.organizacao_final.value = sugestaoAtual.organizacao_sugerida;
  formValidacao.elements.titulo_final.value = sugestaoAtual.titulo_sugerido;
  formValidacao.elements.categoria_final.value = sugestaoAtual.categoria_sugerida;
  formValidacao.elements.prioridade_final.value = sugestaoAtual.prioridade_sugerida;
  formValidacao.elements.observacao.value = "";
}

function renderizarValidacoes() {
  const validacoes = chamadoSelecionado.validacoes_humanas || [];
  if (validacoes.length === 0) {
    validacoesBox.classList.add("hidden");
    listaValidacoes.innerHTML = "";
    return;
  }

  validacoesBox.classList.remove("hidden");
  listaValidacoes.innerHTML = validacoes
    .map((validacao) => `
      <div class="history-item">
        <strong>${escapeHtml(validacao.titulo_final)}</strong>
        <span>${escapeHtml(validacao.organizacao_final)} - ${escapeHtml(validacao.categoria_final)} - ${escapeHtml(validacao.prioridade_final)}</span>
        <small>${escapeHtml(validacao.observacao || "Sem observacao")}</small>
      </div>
    `)
    .join("");
}

function obterUltimaSugestao(chamado) {
  const sugestoes = chamado.sugestoes_ia || [];
  if (sugestoes.length === 0) {
    return null;
  }
  return [...sugestoes].sort((a, b) => b.id - a.id)[0];
}

btnImportarJira.addEventListener("click", importarChamadosDoJira);

btnAnalisar.addEventListener("click", async () => {
  if (!chamadoSelecionado) {
    return;
  }

  btnAnalisar.disabled = true;
  btnAnalisar.textContent = "Analisando...";

  try {
    sugestaoAtual = await requestJson(`/chamados/${chamadoSelecionado.id}/analisar`, {
      method: "POST",
    });
    mostrarMensagem("Sugestao gerada pela IA local da DWPLUS.");
    await carregarChamados();
    await selecionarChamado(chamadoSelecionado.id);
  } catch (error) {
    mostrarMensagem(error.message);
  } finally {
    btnAnalisar.disabled = false;
    btnAnalisar.textContent = "Analisar com IA";
  }
});

formValidacao.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!chamadoSelecionado || !sugestaoAtual) {
    return;
  }

  const formData = new FormData(formValidacao);
  const payload = Object.fromEntries(formData.entries());
  payload.sugestao_id = sugestaoAtual.id;

  try {
    await requestJson(`/chamados/${chamadoSelecionado.id}/validar`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    mostrarMensagem("Validacao humana salva.");
    await carregarChamados();
    await selecionarChamado(chamadoSelecionado.id);
  } catch (error) {
    mostrarMensagem(error.message);
  }
});

btnRecarregar.addEventListener("click", carregarChamados);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

carregarChamados().catch((error) => mostrarMensagem(error.message));
