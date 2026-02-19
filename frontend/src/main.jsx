import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/globals.css';
import 'katex/dist/katex.min.css';

const root = createRoot(document.getElementById('root'));
root.render(<App />);
