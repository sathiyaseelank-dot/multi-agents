const fs = require('fs');
const path = require('path');

const SRC_DIR = path.resolve(__dirname, '..');

describe('Backend Project Structure', () => {
  describe('Required directories', () => {
    const requiredDirs = ['config', 'models', 'middleware', 'routes', 'tests'];

    requiredDirs.forEach((dir) => {
      it(`should have ${dir} directory`, () => {
        const dirPath = path.join(SRC_DIR, dir);
        expect(fs.existsSync(dirPath)).toBe(true);
        expect(fs.statSync(dirPath).isDirectory()).toBe(true);
      });
    });
  });

  describe('Config files', () => {
    it('should have database.js in config directory', () => {
      const dbPath = path.join(SRC_DIR, 'config', 'database.js');
      expect(fs.existsSync(dbPath)).toBe(true);
    });

    it('should export connectDB function from database.js', () => {
      const connectDB = require('../config/database');
      expect(typeof connectDB).toBe('function');
    });
  });

  describe('Model files', () => {
    const modelFiles = ['User.js', 'Conversation.js', 'Message.js', 'index.js'];

    modelFiles.forEach((file) => {
      it(`should have ${file} in models directory`, () => {
        const filePath = path.join(SRC_DIR, 'models', file);
        expect(fs.existsSync(filePath)).toBe(true);
      });
    });

    it('should export all models from models/index.js', () => {
      const models = require('../models');
      expect(models.User).toBeDefined();
      expect(models.Conversation).toBeDefined();
      expect(models.Message).toBeDefined();
    });
  });

  describe('Middleware files', () => {
    it('should have auth.js in middleware directory', () => {
      const authPath = path.join(SRC_DIR, 'middleware', 'auth.js');
      expect(fs.existsSync(authPath)).toBe(true);
    });

    it('should export protect function from auth middleware', () => {
      const { protect } = require('../middleware/auth');
      expect(typeof protect).toBe('function');
    });
  });

  describe('Route files', () => {
    const routeFiles = [
      'authRoutes.js',
      'userRoutes.js',
      'conversationRoutes.js',
      'messageRoutes.js',
    ];

    routeFiles.forEach((file) => {
      it(`should have ${file} in routes directory`, () => {
        const filePath = path.join(SRC_DIR, 'routes', file);
        expect(fs.existsSync(filePath)).toBe(true);
      });
    });

    routeFiles.forEach((file) => {
      it(`${file} should export an Express router`, () => {
        const router = require(path.join('..', 'routes', file));
        expect(typeof router).toBe('function');
        expect(typeof router.get).toBe('function');
        expect(typeof router.post).toBe('function');
        expect(typeof router.put).toBe('function');
        expect(typeof router.delete).toBe('function');
      });
    });
  });

  describe('Entry point', () => {
    it('should have index.js as entry point', () => {
      const indexPath = path.join(SRC_DIR, 'index.js');
      expect(fs.existsSync(indexPath)).toBe(true);
    });
  });

  describe('Environment configuration', () => {
    it('should have .env.example in backend root', () => {
      const envPath = path.resolve(SRC_DIR, '..', '.env.example');
      expect(fs.existsSync(envPath)).toBe(true);
    });

    it('.env.example should define MONGODB_URI', () => {
      const envPath = path.resolve(SRC_DIR, '..', '.env.example');
      const content = fs.readFileSync(envPath, 'utf-8');
      expect(content).toContain('MONGODB_URI');
    });

    it('.env.example should define JWT_SECRET', () => {
      const envPath = path.resolve(SRC_DIR, '..', '.env.example');
      const content = fs.readFileSync(envPath, 'utf-8');
      expect(content).toContain('JWT_SECRET');
    });

    it('.env.example should define PORT', () => {
      const envPath = path.resolve(SRC_DIR, '..', '.env.example');
      const content = fs.readFileSync(envPath, 'utf-8');
      expect(content).toContain('PORT');
    });
  });

  describe('Package configuration', () => {
    it('should have package.json', () => {
      const pkgPath = path.resolve(SRC_DIR, '..', 'package.json');
      expect(fs.existsSync(pkgPath)).toBe(true);
    });

    it('package.json should have required dependencies', () => {
      const pkgPath = path.resolve(SRC_DIR, '..', 'package.json');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));

      expect(pkg.dependencies).toBeDefined();
      expect(pkg.dependencies.express).toBeDefined();
      expect(pkg.dependencies.mongoose).toBeDefined();
      expect(pkg.dependencies.jsonwebtoken).toBeDefined();
      expect(pkg.dependencies.bcryptjs).toBeDefined();
      expect(pkg.dependencies['express-validator']).toBeDefined();
    });

    it('package.json should have test script', () => {
      const pkgPath = path.resolve(SRC_DIR, '..', 'package.json');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));

      expect(pkg.scripts.test).toBeDefined();
      expect(pkg.scripts.test).toContain('jest');
    });

    it('package.json should have dev dependencies for testing', () => {
      const pkgPath = path.resolve(SRC_DIR, '..', 'package.json');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));

      expect(pkg.devDependencies).toBeDefined();
      expect(pkg.devDependencies.jest).toBeDefined();
      expect(pkg.devDependencies.supertest).toBeDefined();
    });
  });
});
