# Deploy - Ju Basilio Viagens

## Estrutura
- **Frontend**: `index.html` (GitHub Pages)
- **Backend**: Flask em `Projeto Agencia/` (Render.com)

## Passo a Passo

### 1. Deploy do Backend no Render

1. Acesse [render.com](https://render.com) e crie uma conta
2. Clique em **"New +"** > **"Web Service"**
3. Conecte seu repositório GitHub: `crinsonex/Agencia`
4. Configuração:
   - **Name**: `agencia-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd "Projeto Agencia" && gunicorn server:app --bind 0.0.0.0:$PORT`
5. Clique em **"Create Web Service"**
6. Aguarde o deploy (2-3 minutos)
7. Copie a URL gerada (ex: `https://agencia-backend.onrender.com`)

### 2. Configurar Frontend

Edite o arquivo `index.html` linha ~273 e substitua:
```javascript
API_BASE = 'https://SEU-BACKEND-AQUI.onrender.com';
```
Pela URL real do seu backend no Render.

### 3. Commit e Push

```bash
git add .
git commit -m "Configurar deploy no Render"
git push origin main
```

### 4. Acessar

- **Frontend**: https://crinsonex.github.io/Agencia/
- **Backend**: https://agencia-backend.onrender.com

## Usuário Padrão

Após o primeiro deploy, o banco cria automaticamente:
- **Usuário**: `admin`
- **Senha**: `admin`
- **Primeiro acesso**: O sistema pedirá para trocar a senha

## Observações

- O Render usa SQLite (`users.db`) que é efêmero. Para produção, use PostgreSQL
- O GitHub Pages só serve arquivos estáticos (HTML/CSS/JS)
- O backend no Render processa o login e serve a API
