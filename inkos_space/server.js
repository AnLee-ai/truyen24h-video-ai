const express = require('express');
const { exec } = require('child_process');
const app = express();

app.use(express.json());

app.post('/generate', (req, res) => {
    const prompt = req.body.prompt;
    if (!prompt) return res.status(400).send({ error: 'Missing prompt' });
    
    // Call the built inkos CLI
    // Note: requires INKOS_LLM_API_KEY environment variable set on Hugging Face
    const cmd = 
ode /app/inkos/packages/cli/dist/index.js interact --message " + prompt.replace(/"/g, '\\"') + ";
    
    exec(cmd, { env: process.env }, (error, stdout, stderr) => {
        if (error) {
            console.error('Error executing inkos:', error);
            // Fallback response if inkos fails
            return res.json({ story: "Ngày xửa ngày xưa có một chú mèo máy. (Lỗi Inkos, đây là văn bản dự phòng)" });
        }
        res.json({ story: stdout.trim() || stderr.trim() });
    });
});

app.get('/', (req, res) => res.send('Inkos API is running on Hugging Face Space'));

const port = process.env.PORT || 7860;
app.listen(port, () => console.log(Server listening on port  + port));
