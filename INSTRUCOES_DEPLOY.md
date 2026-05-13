# Como colocar o Gerador de Contrato MaLuê no ar

Esse guia é em 3 etapas: criar uma conta no GitHub, subir esses arquivos pra lá, e conectar ao Streamlit Community Cloud (que é gratuito). No final você vai ter um link tipo `https://malue-contratos.streamlit.app` que pode usar no celular.

Você só faz esse processo uma vez. Depois, sempre que quiser gerar um contrato, é só abrir o link.

---

## Etapa 1 — Conta no GitHub (3 minutos)

1. Acesse https://github.com/signup
2. Crie uma conta com o email `malueoficial@gmail.com` (ou outro de sua preferência).
3. Confirme o email.

Pronto. Não precisa instalar nada nem mexer em código.

---

## Etapa 2 — Subir os arquivos pro GitHub (5 minutos)

A forma mais fácil é pela interface web do GitHub, arrastando os arquivos:

1. Logada no GitHub, clique no botão verde **"New"** no canto superior esquerdo (ou vá em https://github.com/new).
2. Em **Repository name**, coloque: `malue-contratos`
3. Marque a opção **Public** (precisa ser público pra usar o plano gratuito do Streamlit Cloud — fique tranquila, ninguém acha seu repositório se não souber o nome).
4. Marque também **Add a README file**.
5. Clique em **Create repository**.

Agora você vai estar dentro do seu repositório vazio. Hora de subir os arquivos:

6. Clique no botão **"Add file"** (perto do canto superior direito) → **"Upload files"**.
7. Abra a pasta `gerador_contrato_malue` (essa mesma pasta que tem este arquivo) no seu Finder.
8. Selecione **todos** os arquivos e a pasta `assets/` e arraste pra área de upload no navegador. Importante: o conteúdo da pasta `assets/` precisa ir junto.
9. Role a página até o final e clique em **Commit changes**.

Se tudo deu certo, você vai ver os arquivos listados: `app.py`, `contrato.py`, `utils.py`, `requirements.txt`, `INSTRUCOES_DEPLOY.md` e a pasta `assets/`.

---

## Etapa 3 — Conectar ao Streamlit Cloud (3 minutos)

1. Acesse https://share.streamlit.io
2. Clique em **Sign up** e escolha **Continue with GitHub** (vai usar a conta que você acabou de criar).
3. Autorize o Streamlit a acessar seus repositórios.
4. Já logada, clique em **Create app** (canto superior direito) → **Deploy a public app from GitHub**.
5. Preencha os campos:
   - **Repository**: `seu-usuario/malue-contratos` (vai aparecer na lista)
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: escolha algo memorável tipo `malue-contratos` → vai virar `https://malue-contratos.streamlit.app`
6. Clique em **Deploy**.

Espera uns 2-3 minutos enquanto ele instala as dependências e inicia. Quando aparecer a tela com o formulário, está pronto.

---

## Etapa 4 — Salvar como atalho no celular (1 minuto)

No iPhone:
1. Abra o link `https://malue-contratos.streamlit.app` no Safari.
2. Toque no ícone de compartilhar (quadrado com seta pra cima) na barra inferior.
3. Role até **"Adicionar à Tela de Início"**.
4. Renomeie pra "Contratos MaLuê" e toque em **Adicionar**.

Agora você tem um ícone na tela inicial que abre o gerador direto. Funciona quase como um app.

---

## Como usar (no celular ou no computador)

1. Abra o link / ícone.
2. Preencha os campos: nome do contratante, CPF/CNPJ, endereço, dados do show, valor.
3. Clique em **Gerar contrato**.
4. Toque em **Baixar contrato em PDF** — o PDF vai pros downloads do celular.
5. (Opcional) Toque em **Abrir WhatsApp com mensagem pronta** — o WhatsApp abre com uma mensagem padrão; você escolhe o contato e anexa o PDF que acabou de baixar.

---

## Como mudar alguma coisa no contrato depois

Se algum dia você quiser mudar texto fixo (tipo dados bancários, alguma cláusula, valor da multa, etc.), me chama aqui no Claude que eu edito o arquivo `contrato.py` e te explico como subir a nova versão pro GitHub (é só editar o arquivo direto pela interface web — sem instalar nada).

---

## Custos

Tudo gratuito:
- **GitHub Free**: repositório público ilimitado.
- **Streamlit Community Cloud**: 1 app público gratuito (que é o que a gente precisa).

A única "pegadinha" do plano gratuito do Streamlit é que se o app ficar **uns dias sem acesso**, ele "dorme" pra economizar recursos. Quando você abre de novo, demora uns 30 segundos pra acordar. Como você vai gerar contratos com frequência, isso quase não acontece.
