const connectDB = require('../config/database');

jest.mock('mongoose', () => {
  const mockConn = {
    connection: { host: 'localhost:27017' },
  };
  return {
    connect: jest.fn().mockResolvedValue(mockConn),
  };
});

describe('Database Configuration', () => {
  const originalEnv = process.env;
  const originalExit = process.exit;
  const originalConsoleLog = console.log;
  const originalConsoleError = console.error;

  beforeEach(() => {
    process.env = { ...originalEnv, MONGODB_URI: 'mongodb://localhost:27017/testdb' };
    process.exit = jest.fn();
    console.log = jest.fn();
    console.error = jest.fn();
  });

  afterEach(() => {
    process.env = originalEnv;
    process.exit = originalExit;
    console.log = originalConsoleLog;
    console.error = originalConsoleError;
    jest.clearAllMocks();
  });

  it('should connect to MongoDB successfully', async () => {
    const mongoose = require('mongoose');
    mongoose.connect.mockResolvedValueOnce({
      connection: { host: 'localhost:27017' },
    });

    const conn = await connectDB();

    expect(mongoose.connect).toHaveBeenCalledWith(
      'mongodb://localhost:27017/testdb',
      expect.objectContaining({
        maxPoolSize: 10,
        serverSelectionTimeoutMS: 5000,
        socketTimeoutMS: 45000,
      })
    );
    expect(conn).toBeDefined();
    expect(conn.connection.host).toBe('localhost:27017');
  });

  it('should log connection host on success', async () => {
    const mongoose = require('mongoose');
    mongoose.connect.mockResolvedValueOnce({
      connection: { host: 'localhost:27017' },
    });

    await connectDB();
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('MongoDB Connected')
    );
  });

  it('should exit process on connection failure', async () => {
    const mongoose = require('mongoose');
    mongoose.connect.mockRejectedValueOnce(new Error('Connection refused'));

    await connectDB();

    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Connection refused')
    );
    expect(process.exit).toHaveBeenCalledWith(1);
  });

  it('should handle authentication errors', async () => {
    const mongoose = require('mongoose');
    mongoose.connect.mockRejectedValueOnce(new Error('Authentication failed'));

    await connectDB();

    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Authentication failed')
    );
    expect(process.exit).toHaveBeenCalledWith(1);
  });

  it('should handle timeout errors', async () => {
    const mongoose = require('mongoose');
    mongoose.connect.mockRejectedValueOnce(new Error('Server selection timed out'));

    await connectDB();

    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Server selection timed out')
    );
    expect(process.exit).toHaveBeenCalledWith(1);
  });
});
