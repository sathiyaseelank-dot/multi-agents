describe('Models Index', () => {
  beforeEach(() => {
    jest.resetModules();
  });

  it('should export User model', () => {
    const { User } = require('../models');
    expect(User).toBeDefined();
    expect(User.modelName).toBe('User');
  });

  it('should export Conversation model', () => {
    const { Conversation } = require('../models');
    expect(Conversation).toBeDefined();
    expect(Conversation.modelName).toBe('Conversation');
  });

  it('should export Message model', () => {
    const { Message } = require('../models');
    expect(Message).toBeDefined();
    expect(Message.modelName).toBe('Message');
  });

  it('should export exactly three models', () => {
    const models = require('../models');
    const keys = Object.keys(models);
    expect(keys).toHaveLength(3);
    expect(keys).toContain('User');
    expect(keys).toContain('Conversation');
    expect(keys).toContain('Message');
  });

  it('should export User as a Mongoose model with expected fields', () => {
    const { User } = require('../models');
    const schema = User.schema;

    expect(schema.path('username')).toBeDefined();
    expect(schema.path('email')).toBeDefined();
    expect(schema.path('password')).toBeDefined();
    expect(schema.path('avatar')).toBeDefined();
    expect(schema.path('status')).toBeDefined();
    expect(schema.path('lastSeen')).toBeDefined();
    expect(schema.path('conversations')).toBeDefined();
  });

  it('should export Conversation as a Mongoose model with expected fields', () => {
    const { Conversation } = require('../models');
    const schema = Conversation.schema;

    expect(schema.path('type')).toBeDefined();
    expect(schema.path('name')).toBeDefined();
    expect(schema.path('description')).toBeDefined();
    expect(schema.path('participants')).toBeDefined();
    expect(schema.path('lastMessage')).toBeDefined();
    expect(schema.path('lastMessageAt')).toBeDefined();
    expect(schema.path('unreadCount')).toBeDefined();
    expect(schema.path('isActive')).toBeDefined();
  });

  it('should export Message as a Mongoose model with expected fields', () => {
    const { Message } = require('../models');
    const schema = Message.schema;

    expect(schema.path('conversationId')).toBeDefined();
    expect(schema.path('sender')).toBeDefined();
    expect(schema.path('content')).toBeDefined();
    expect(schema.path('messageType')).toBeDefined();
    expect(schema.path('mediaUrl')).toBeDefined();
    expect(schema.path('mediaType')).toBeDefined();
    expect(schema.path('replyTo')).toBeDefined();
    expect(schema.path('reactions')).toBeDefined();
    expect(schema.path('isEdited')).toBeDefined();
    expect(schema.path('isDeleted')).toBeDefined();
    expect(schema.path('deletedAt')).toBeDefined();
    expect(schema.path('readBy')).toBeDefined();
  });

  it('should have User schema with password select false', () => {
    const { User } = require('../models');
    const passwordPath = User.schema.path('password');
    expect(passwordPath.options.select).toBe(false);
  });

  it('should have User with matchPassword method', () => {
    const { User } = require('../models');
    const user = new User({
      username: 'test',
      email: 'test@test.com',
      password: 'password123',
    });
    expect(typeof user.matchPassword).toBe('function');
  });

  it('should have User with toJSON method that excludes password', () => {
    const { User } = require('../models');
    const user = new User({
      username: 'test',
      email: 'test@test.com',
      password: 'password123',
    });
    expect(typeof user.toJSON).toBe('function');
  });

  it('should have Conversation with getParticipantIds method', () => {
    const { Conversation } = require('../models');
    const conversation = new Conversation({ type: 'direct' });
    expect(typeof conversation.getParticipantIds).toBe('function');
  });

  it('should have Conversation with isParticipant method', () => {
    const { Conversation } = require('../models');
    const conversation = new Conversation({ type: 'direct' });
    expect(typeof conversation.isParticipant).toBe('function');
  });

  it('should have Message with isReadBy method', () => {
    const { Message } = require('../models');
    const message = new Message({
      conversationId: '000000000000000000000000',
      sender: '000000000000000000000000',
      content: 'test',
    });
    expect(typeof message.isReadBy).toBe('function');
  });

  it('should have Message with addReaction method', () => {
    const { Message } = require('../models');
    const message = new Message({
      conversationId: '000000000000000000000000',
      sender: '000000000000000000000000',
      content: 'test',
    });
    expect(typeof message.addReaction).toBe('function');
  });

  it('should have Message with removeReaction method', () => {
    const { Message } = require('../models');
    const message = new Message({
      conversationId: '000000000000000000000000',
      sender: '000000000000000000000000',
      content: 'test',
    });
    expect(typeof message.removeReaction).toBe('function');
  });
});
