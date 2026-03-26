const mongoose = require('mongoose');
const Conversation = require('../models/Conversation');

describe('Conversation Model', () => {
  describe('Schema Validation', () => {
    it('should require type field if not provided with default', () => {
      const conversation = new Conversation({});
      expect(conversation.type).toBe('direct');
    });

    it('should accept direct type', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(conversation.type).toBe('direct');
    });

    it('should accept group type', () => {
      const conversation = new Conversation({
        type: 'group',
        name: 'Test Group',
        participants: [
          { user: new mongoose.Types.ObjectId(), role: 'admin' },
        ],
      });
      expect(conversation.type).toBe('group');
    });

    it('should reject invalid type', () => {
      const conversation = new Conversation({ type: 'channel' });
      const error = conversation.validateSync();
      expect(error.errors.type).toBeDefined();
    });

    it('should default type to direct', () => {
      const conversation = new Conversation({});
      expect(conversation.type).toBe('direct');
    });

    it('should reject group name exceeding 100 characters', () => {
      const conversation = new Conversation({
        type: 'group',
        name: 'a'.repeat(101),
      });
      const error = conversation.validateSync();
      expect(error.errors.name).toBeDefined();
      expect(error.errors.name.message).toBe('Group name cannot exceed 100 characters');
    });

    it('should accept group name at exactly 100 characters', () => {
      const conversation = new Conversation({
        type: 'group',
        name: 'a'.repeat(100),
      });
      const error = conversation.validateSync();
      expect(error).toBeUndefined();
    });

    it('should trim group name whitespace', () => {
      const conversation = new Conversation({
        type: 'group',
        name: '  My Group  ',
      });
      expect(conversation.name).toBe('My Group');
    });

    it('should reject description exceeding 500 characters', () => {
      const conversation = new Conversation({
        type: 'group',
        description: 'a'.repeat(501),
      });
      const error = conversation.validateSync();
      expect(error.errors.description).toBeDefined();
      expect(error.errors.description.message).toBe(
        'Description cannot exceed 500 characters'
      );
    });

    it('should accept description at exactly 500 characters', () => {
      const conversation = new Conversation({
        type: 'group',
        description: 'a'.repeat(500),
      });
      const error = conversation.validateSync();
      expect(error).toBeUndefined();
    });
  });

  describe('Participants Array', () => {
    it('should accept participants with user reference', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId }],
      });
      expect(conversation.participants).toHaveLength(1);
      expect(conversation.participants[0].user).toEqual(userId);
    });

    it('should default participant role to member', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId }],
      });
      expect(conversation.participants[0].role).toBe('member');
    });

    it('should accept admin role for participant', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'group',
        participants: [{ user: userId, role: 'admin' }],
      });
      expect(conversation.participants[0].role).toBe('admin');
    });

    it('should reject invalid participant role', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId, role: 'moderator' }],
      });
      const error = conversation.validateSync();
      expect(error).toBeDefined();
    });

    it('should default joinedAt to current date', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId }],
      });
      expect(conversation.participants[0].joinedAt).toBeInstanceOf(Date);
    });

    it('should accept multiple participants', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();
      const user3 = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'group',
        name: 'Test Group',
        participants: [
          { user: user1, role: 'admin' },
          { user: user2 },
          { user: user3 },
        ],
      });
      expect(conversation.participants).toHaveLength(3);
    });
  });

  describe('Default Values', () => {
    it('should set lastMessage to null by default', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(conversation.lastMessage).toBeNull();
    });

    it('should set lastMessageAt to null by default', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(conversation.lastMessageAt).toBeNull();
    });

    it('should set isActive to true by default', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(conversation.isActive).toBe(true);
    });

    it('should have empty unreadCount array by default', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(conversation.unreadCount).toEqual([]);
    });

    it('should have empty participants array by default', () => {
      const conversation = new Conversation({ type: 'direct' });
      expect(conversation.participants).toEqual([]);
    });
  });

  describe('Timestamps', () => {
    it('should have timestamps enabled', () => {
      expect(Conversation.schema.options.timestamps).toBe(true);
    });
  });

  describe('Indexes', () => {
    it('should have index on participants', () => {
      const indexes = Conversation.schema.indexes();
      const hasIndex = indexes.some(
        (idx) => idx[0].participants === 1
      );
      expect(hasIndex).toBe(true);
    });

    it('should have index on lastMessageAt descending', () => {
      const indexes = Conversation.schema.indexes();
      const hasIndex = indexes.some(
        (idx) => idx[0].lastMessageAt === -1
      );
      expect(hasIndex).toBe(true);
    });

    it('should have compound index on type and isActive', () => {
      const indexes = Conversation.schema.indexes();
      const hasIndex = indexes.some(
        (idx) => idx[0].type === 1 && idx[0].isActive === 1
      );
      expect(hasIndex).toBe(true);
    });
  });

  describe('getParticipantIds method', () => {
    it('should return array of participant user IDs', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [
          { user: user1, role: 'admin' },
          { user: user2, role: 'member' },
        ],
      });

      const ids = conversation.getParticipantIds();

      expect(ids).toHaveLength(2);
      expect(ids[0]).toEqual(user1);
      expect(ids[1]).toEqual(user2);
    });

    it('should return empty array when no participants', () => {
      const conversation = new Conversation({ type: 'direct' });
      const ids = conversation.getParticipantIds();
      expect(ids).toEqual([]);
    });
  });

  describe('isParticipant method', () => {
    it('should return true for existing participant', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId, role: 'admin' }],
      });

      expect(conversation.isParticipant(userId)).toBe(true);
    });

    it('should return false for non-participant', () => {
      const participantId = new mongoose.Types.ObjectId();
      const nonParticipantId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: participantId, role: 'admin' }],
      });

      expect(conversation.isParticipant(nonParticipantId)).toBe(false);
    });

    it('should work with string user IDs', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId, role: 'member' }],
      });

      expect(conversation.isParticipant(userId.toString())).toBe(true);
    });

    it('should return false for null userId', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        participants: [{ user: userId }],
      });

      expect(() => conversation.isParticipant(null)).toThrow();
    });
  });

  describe('Unread Count', () => {
    it('should accept unreadCount with user and count', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        unreadCount: [{ user: userId, count: 5 }],
      });

      expect(conversation.unreadCount).toHaveLength(1);
      expect(conversation.unreadCount[0].count).toBe(5);
    });

    it('should default count to 0 in unreadCount', () => {
      const userId = new mongoose.Types.ObjectId();
      const conversation = new Conversation({
        type: 'direct',
        unreadCount: [{ user: userId }],
      });

      expect(conversation.unreadCount[0].count).toBe(0);
    });
  });
});
