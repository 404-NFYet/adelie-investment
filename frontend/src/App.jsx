import { useState } from 'react';

function App() {
  const [isDarkMode, setIsDarkMode] = useState(false);

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <div className="min-h-screen bg-background text-text-primary transition-colors duration-300">
      <header className="p-4 border-b border-border">
        <div className="max-w-mobile mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold">
            <span className="text-primary">Narrative</span> Investment
          </h1>
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-lg bg-surface hover:bg-border transition-colors"
            aria-label="Toggle dark mode"
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <main className="max-w-mobile mx-auto p-4">
        <section className="mt-8 text-center">
          <h2 className="text-2xl font-bold mb-4">
            AI 기반 투자 스토리텔링
          </h2>
          <p className="text-text-secondary mb-6">
            복잡한 투자를 쉬운 이야기로
          </p>
          <p className="font-handwriting text-3xl text-primary">
            Your Investment Journey Starts Here
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;
