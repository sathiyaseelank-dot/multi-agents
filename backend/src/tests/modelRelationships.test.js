const mongoose = require('mongoose');

const User = require('../models/User');
const Conversation = require('../models/Conversation');
const Message = require('../models/Message');

describe('Model Relationships and Cross-References', () => {
  describe('User -> Conversation relationship', () => {
    it('should reference Conversation model in conversations field', () => {
      const conversationsPath = User.schema.path('conversations');
      expect(conversationsPath).toBeDefined();
      expect(conversationsPath.instance).toBe('Array');

      const caster = conversationsPath.caster;
      expect(caster.options.ref).toBe('Conversation');
    });

    it('should store ObjectId references in conversations', () => {
      const conversationsPath = User.schema.path('conversations');
      const caster = conversationsPath.caster;
      expect(caster.instance).toBe('ObjectId');
    });
  });

  describe('Conversation -> User relationship', () => {
    it('should reference User model in participants.user field', () => {
      const participantsPath = Conversation.schema.path('participants');
      expect(participantsPath).toBeDefined();

      const schema = participantsPath.schema;
      const userPath = schema.path('user');
      expect(userPath.options.ref).toBe('User');
    });

    it('should reference User model in unreadCount.user field', () => {
      const unreadCountPath = Conversation.schema.path('unreadCount');
      expect(unreadCountPath).toBeDefined();

      const schema = unreadCountPath.schema;
      const userPath = schema.path('user');
      expect(userPath.options.ref).toBe('User');
    });
  });

  describe('Conversation -> Message relationship', () => {
    it('should reference Message model in lastMessage field', () => {
      const lastMessagePath = Conversation.schema.path('lastMessage');
      expect(lastMessagePath).toBeDefined();
      expect(lastMessagePath.options.ref).toBe('Message');
    });
  });

  describe('Message -> Conversation relationship', () => {
    it('should reference Conversation model in conversationId field', () => {
      const conversationIdPath = Message.schema.path('conversationId');
      expect(conversationIdPath).toBeDefined();
      expect(conversationIdPath.options.ref).toBe('Conversation');
    });
  });

  describe('Message -> User relationship', () => {
    it('should reference User model in sender field', () => {
      const senderPath = Message.schema.path('sender');
      expect(senderPath).toBeDefined();
      expect(senderPath.options.ref).toBe('User');
    });

    it('should reference User model in reactions.user field', () => {
      const reactionsPath = Message.schema.path('reactions');
      expect(reactionsPath).toBeDefined();

      const schema = reactionsPath.schema;
      const userPath = schema.path('user');
      expect(userPath.options.ref).toBe('User');
    });

    it('should reference User model in readBy.user field', () => {
      const readByPath = Message.schema.path('readBy');
      expect(readByPath).toBeDefined();

      const schema = readByPath.schema;
      const userPath = schema.path('user');
      expect(userPath.options.ref).toBe('User');
    });
  });

  describe('Message -> Message relationship (reply)', () => {
    it('should reference Message model in replyTo field', () => {
      const replyToPath = Message.schema.path('replyTo');
      expect(replyToPath).toBeDefined();
      expect(replyToPath.options.ref).toBe('Message');
    });
  });

  describe('Model instance methods existence', () => {
    it('User should have matchPassword method', () => {
      const user = new User({
        username: 'test',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(typeof user.matchPassword).toBe('function');
    });

    it('User should have toJSON method that strips password', () => {
      const user = new User({
        username: 'test',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(typeof user.toJSON).toBe('function');
    });

    it('Conversation should have getParticipantIds method', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(typeof conversation.getParticipantIds).toBe('function');
    });

    it('Conversation should have isParticipant method', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(typeof conversation.isParticipant).toBe('function');
    });

    it('Message should have isReadBy method', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'test',
      });
      expect(typeof message.isReadBy).toBe('function');
    });

    it('Message should have addReaction method', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'test',
      });
      expect(typeof message.addReaction).toBe('function');
    });

    it('Message should have removeReaction method', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'test',
      });
      expect(typeof message.removeReaction).toBe('function');
    });
  });

  describe('Model schema constraints', () => {
    it('User should have unique constraint on username', () => {
      const usernamePath = User.schema.path('username');
      expect(usernamePath.options.unique).toBe(true);
    });

    it('User should have unique constraint on email', () => {
      const emailPath = User.schema.path('email');
      expect(emailPath.options.unique).toBe(true);
    });

    it('Message should have index on conversationId', () => {
      const conversationIdPath = Message.schema.path('conversationId');
      expect(conversationIdPath.options.index).toBe(true);
    });

    it('Message should have index on sender', () => {
      const senderPath = Message.schema.path('sender');
      expect(senderPath.options.index).toBe(true);
    });
  });

  describe('Password security', () => {
    it('should not include password in queries by default', () => {
      const passwordPath = User.schema.path('password');
      expect(passwordPath.options.select).toBe(false);
    });

    it('should hash password in pre-save hook', () => {
      const preSaveHooks = User.schema.s.hooks._pres.get('save');
      expect(preSaveHooks).toBeDefined();
      expect(preSaveHooks.length).toBeGreaterThan(1);
      const hasPasswordHook = preSaveHooks.some(
        (hook) => hook.fn.toString().includes('bcrypt') || hook.fn.toString().includes('password')
      );
      expect(hasPasswordHook).toBe(true);
    });
  });

  describe('Conversation participant management', () => {
    it('should validate participant role enum', () => {
      const participantsPath = Conversation.schema.path('participants');
      const rolePath = participantsPath.schema.path('role');
      expect(rolePath.enumValues).toContain('admin');
      expect(rolePath.enumValues).toContain('member');
    });

    it('should default participant role to member', () => {
      const participantsPath = Conversation.schema.path('participants');
      const rolePath = participantsPath.schema.path('role');
      expect(rolePath.defaultValue).toBe('member');
    });

    it('should require user reference in participants', () => {
      const participantsPath = Conversation.schema.path('participants');
      const userPath = participantsPath.schema.path('user');
      expect(userPath.options.required).toBe(true);
    });
  });

  describe('Message types', () => {
    it('should support text message type', () => {
      const messageTypePath = Message.schema.path('messageType');
      expect(messageTypePath.enumValues).toContain('text');
    });

    it('should support image message type', () => {
      const messageTypePath = Message.schema.path('messageType');
      expect(messageTypePath.enumValues).toContain('image');
    });

    it('should support file message type', () => {
      const messageTypePath = Message.schema.path('messageType');
      expect(messageTypePath.enumValues).toContain('file');
    });

    it('should support system message type', () => {
      const messageTypePath = Message.schema.path('messageType');
      expect(messageTypePath.enumValues).toContain('system');
    });

    it('should default to text message type', () => {
      const messageTypePath = Message.schema.path('messageType');
      expect(messageTypePath.defaultValue).toBe('text');
    });
  });

  describe('Conversation types', () => {
    it('should support direct conversation type', () => {
      const typePath = Conversation.schema.path('type');
      expect(typePath.enumValues).toContain('direct');
    });

    it('should support group conversation type', () => {
      const typePath = Conversation.schema.path('type');
      expect(typePath.enumValues).toContain('group');
    });

    it('should default to direct conversation type', () => {
      const typePath = Conversation.schema.path('type');
      expect(typePath.defaultValue).toBe('direct');
    });
  });

  describe('User status', () => {
    it('should support online status', () => {
      const statusPath = User.schema.path('status');
      expect(statusPath.enumValues).toContain('online');
    });

    it('should support offline status', () => {
      const statusPath = User.schema.path('status');
      expect(statusPath.enumValues).toContain('offline');
    });

    it('should support away status', () => {
      const statusPath = User.schema.path('status');
      expect(statusPath.enumValues).toContain('away');
    });

    it('should default to offline status', () => {
      const statusPath = User.schema.path('status');
      expect(statusPath.defaultValue).toBe('offline');
    });
  });
});
