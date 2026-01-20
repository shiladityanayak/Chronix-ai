import React from 'react';
import { motion } from 'framer-motion';

function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white font-sans antialiased">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-6 bg-gray-800/50 backdrop-blur-md sticky top-0 z-50 border-b border-gray-700">
        <div className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
          Chronix
        </div>
        <div className="hidden md:flex space-x-8">
          <a href="#features" className="hover:text-blue-400 transition">Features</a>
          <a href="#about" className="hover:text-blue-400 transition">About</a>
          <a href="http://localhost:5000/login" className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-full font-semibold transition shadow-lg shadow-blue-500/30">
            Login
          </a>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="min-h-screen flex flex-col items-center justify-center text-center px-4 relative overflow-hidden -mt-20">
        {/* Background Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/20 rounded-full blur-[100px] pointer-events-none"></div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-6xl md:text-8xl font-extrabold mb-6 relative z-10"
        >
          Level Up Your <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">Community</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-xl text-gray-300 mb-10 max-w-2xl"
        >
          The all-in-one Discord bot featuring advanced moderation, deep economy systems, high-quality music, and more.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="space-x-4"
        >
          <a href="#" className="bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-bold hover:bg-blue-700 shadow-xl transition transform hover:scale-105 inline-block">
            Invite Chronix
          </a>
          <a href="http://localhost:5000/dashboard" className="bg-gray-800 text-white px-8 py-4 rounded-xl text-lg font-bold hover:bg-gray-700 border border-gray-700 transition transform hover:scale-105 inline-block">
            Dashboard
          </a>
        </motion.div>
      </header>

      {/* Features Grid */}
      <section id="features" className="py-24 px-8 bg-gray-900 relative">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">Why Chronix?</h2>
          <p className="text-gray-400">Built for performance. Designed for community.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <FeatureCard
            icon="🛡️"
            title="Moderation"
            desc="Automod, Logging, and Tickets to keep your server safe and organized."
          />
          <FeatureCard
            icon="💰"
            title="Economy"
            desc="Global shops, trading, gambling, and items to engage your members."
          />
          <FeatureCard
            icon="🎵"
            title="Music"
            desc="Lag-free high-quality streaming from your favorite sources."
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-800 py-10 text-center text-gray-500 border-t border-gray-700">
        <p>&copy; 2024 Chronix Bot. Crafted with ❤️.</p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, desc }) {
  return (
    <div className="bg-gray-800/50 backdrop-blur-sm p-8 rounded-2xl border border-gray-700 hover:border-blue-500/50 transition duration-300 hover:shadow-2xl hover:shadow-blue-500/10 group">
      <div className="text-4xl mb-4 group-hover:scale-110 transition duration-300">{icon}</div>
      <h3 className="text-2xl font-bold mb-2">{title}</h3>
      <p className="text-gray-400">{desc}</p>
    </div>
  );
}

export default App;
