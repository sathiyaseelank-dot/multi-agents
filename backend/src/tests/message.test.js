const mongoose = require('mongoose');
const Message = require('../models/Message');

describe('Message Model', () => {
  describe('Schema Validation', () => {
    it('should require conversationId', () => {
      const message = new Message({
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      const error = message.validateSync();
      expect(error.errors.conversationId).toBeDefined();
      expect(error.errors.conversationId.message).toBe('Conversation ID is required');
    });

    it('should require sender', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      const error = message.validateSync();
      expect(error.errors.sender).toBeDefined();
      expect(error.errors.sender.message).toBe('Sender is required');
    });

    it('should require content for text messages', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'text',
      });
      const error = message.validateSync();
      expect(error.errors.content).toBeDefined();
    });

    it('should not require content for system messages', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'system',
      });
      const error = message.validateSync();
      expect(error).toBeUndefined();
    });

    it('should not require content for image messages', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'image',
        mediaUrl: 'http://example.com/image.png',
      });
      const error = message.validateSync();
      expect(error).toBeUndefined();
    });

    it('should not require content for file messages', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'file',
        mediaUrl: 'http://example.com/file.pdf',
      });
      const error = message.validateSync();
      expect(error).toBeUndefined();
    });

    it('should reject content exceeding 5000 characters', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'a'.repeat(5001),
      });
      const error = message.validateSync();
      expect(error.errors.content).toBeDefined();
      expect(error.errors.content.message).toBe(
        'Message cannot exceed 5000 characters'
      );
    });

    it('should accept content at exactly 5000 characters', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'a'.repeat(5000),
      });
      const error = message.validateSync();
      expect(error).toBeUndefined();
    });

    it('should be valid with all required fields', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello, World!',
      });
      const error = message.validateSync();
      expect(error).toBeUndefined();
    });
  });

  describe('MessageType Enum', () => {
    it('should accept text messageType', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        messageType: 'text',
      });
      expect(message.messageType).toBe('text');
    });

    it('should accept image messageType', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'image',
        mediaUrl: 'http://example.com/img.png',
      });
      expect(message.messageType).toBe('image');
    });

    it('should accept file messageType', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'file',
        mediaUrl: 'http://example.com/doc.pdf',
      });
      expect(message.messageType).toBe('file');
    });

    it('should accept system messageType', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'system',
      });
      expect(message.messageType).toBe('system');
    });

    it('should default messageType to text', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.messageType).toBe('text');
    });

    it('should reject invalid messageType', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        messageType: 'video',
      });
      const error = message.validateSync();
      expect(error).toBeDefined();
    });
  });

  describe('Default Values', () => {
    it('should set mediaUrl to null by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.mediaUrl).toBeNull();
    });

    it('should set mediaType to null by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.mediaType).toBeNull();
    });

    it('should set replyTo to null by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.replyTo).toBeNull();
    });

    it('should set isEdited to false by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.isEdited).toBe(false);
    });

    it('should set isDeleted to false by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.isDeleted).toBe(false);
    });

    it('should set deletedAt to null by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.deletedAt).toBeNull();
    });

    it('should have empty reactions array by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.reactions).toEqual([]);
    });

    it('should have empty readBy array by default', () => {
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });
      expect(message.readBy).toEqual([]);
    });
  });

  describe('Timestamps', () => {
    it('should have timestamps enabled', () => {
      expect(Message.schema.options.timestamps).toBe(true);
    });
  });

  describe('Indexes', () => {
    it('should have compound index on conversationId and createdAt', () => {
      const indexes = Message.schema.indexes();
      const hasIndex = indexes.some(
        (idx) => idx[0].conversationId === 1 && idx[0].createdAt === -1
      );
      expect(hasIndex).toBe(true);
    });

    it('should have index on sender', () => {
      const indexes = Message.schema.indexes();
      const hasIndex = indexes.some((idx) => idx[0].sender === 1);
      expect(hasIndex).toBe(true);
    });

    it('should have index on createdAt', () => {
      const indexes = Message.schema.indexes();
      const hasIndex = indexes.some((idx) => idx[0].createdAt === -1);
      expect(hasIndex).toBe(true);
    });
  });

  describe('isReadBy method', () => {
    it('should return true when user has read the message', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        readBy: [{ user: userId, readAt: new Date() }],
      });

      expect(message.isReadBy(userId)).toBe(true);
    });

    it('should return false when user has not read the message', () => {
      const readerId = new mongoose.Types.ObjectId();
      const nonReaderId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        readBy: [{ user: readerId, readAt: new Date() }],
      });

      expect(message.isReadBy(nonReaderId)).toBe(false);
    });

    it('should work with string user ID', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        readBy: [{ user: userId }],
      });

      expect(message.isReadBy(userId.toString())).toBe(true);
    });
  });

  describe('addReaction method', () => {
    it('should add a new reaction', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });

      message.addReaction(userId, '👍');

      expect(message.reactions).toHaveLength(1);
      expect(message.reactions[0].user).toEqual(userId);
      expect(message.reactions[0].emoji).toBe('👍');
    });

    it('should not add duplicate reaction from same user with same emoji', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        reactions: [{ user: userId, emoji: '👍' }],
      });

      message.addReaction(userId, '👍');

      expect(message.reactions).toHaveLength(1);
    });

    it('should allow same user to add different emoji reactions', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });

      message.addReaction(userId, '👍');
      message.addReaction(userId, '❤️');

      expect(message.reactions).toHaveLength(2);
    });

    it('should allow different users to add same emoji', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });

      message.addReaction(user1, '👍');
      message.addReaction(user2, '👍');

      expect(message.reactions).toHaveLength(2);
    });

    it('should return the message instance', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });

      const result = message.addReaction(userId, '👍');
      expect(result).toBe(message);
    });
  });

  describe('removeReaction method', () => {
    it('should remove existing reaction', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        reactions: [{ user: userId, emoji: '👍' }],
      });

      message.removeReaction(userId, '👍');

      expect(message.reactions).toHaveLength(0);
    });

    it('should not affect other reactions when removing', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        reactions: [
          { user: user1, emoji: '👍' },
          { user: user2, emoji: '👍' },
          { user: user1, emoji: '❤️' },
        ],
      });

      message.removeReaction(user1, '👍');

      expect(message.reactions).toHaveLength(2);
      expect(message.reactions.find((r) => r.user.equals(user2) && r.emoji === '👍')).toBeDefined();
      expect(message.reactions.find((r) => r.user.equals(user1) && r.emoji === '❤️')).toBeDefined();
    });

    it('should not throw when removing non-existent reaction', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        reactions: [],
      });

      expect(() => message.removeReaction(userId, '👍')).not.toThrow();
      expect(message.reactions).toHaveLength(0);
    });

    it('should return the message instance', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
      });

      const result = message.removeReaction(userId, '👍');
      expect(result).toBe(message);
    });
  });

  describe('Read Tracking', () => {
    it('should set default readAt date', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        readBy: [{ user: userId }],
      });

      expect(message.readBy[0].readAt).toBeInstanceOf(Date);
    });
  });

  describe('Reactions Schema', () => {
    it('should set default createdAt for reactions', () => {
      const userId = new mongoose.Types.ObjectId();
      const message = new Message({
        conversationId: new mongoose.Types.ObjectId(),
        sender: new mongoose.Types.ObjectId(),
        content: 'Hello',
        reactions: [{ user: userId, emoji: '👍' }],
      });

      expect(message.reactions[0].createdAt).toBeInstanceOf(Date);
    });
  });
});
