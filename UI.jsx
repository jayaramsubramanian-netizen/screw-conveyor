<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Starting…</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #1e3a5f 0%, #0f2444 100%);
  font-family: 'Segoe UI', system-ui, sans-serif;
  color: white;
  user-select: none;
}
.icon { font-size: 64px; margin-bottom: 24px; animation: spin 3s linear infinite; }
@keyframes spin { 0%,100% { transform: rotate(0deg); } 50% { transform: rotate(20deg); } }
h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
p  { font-size: 14px; color: #93c5fd; margin-bottom: 32px; }
.bar { width: 300px; height: 4px; background: rgba(255,255,255,.15); border-radius: 99px; overflow: hidden; }
.fill { height: 100%; background: #3b82f6; border-radius: 99px; animation: load 2s ease-in-out infinite; }
@keyframes load { 0% { width: 0%; } 70% { width: 85%; } 100% { width: 85%; } }
.status { margin-top: 16px; font-size: 12px; color: #64748b; }
</style>
</head>
<body>
  <div class="icon">🔩</div>
  <h1>Screw Conveyor Designer</h1>
  <p>Starting calculation engine…</p>
  <div class="bar"><div class="fill"></div></div>
  <p class="status">Loading CEMA · KWS · DIN modules</p>
</body>
</html>
