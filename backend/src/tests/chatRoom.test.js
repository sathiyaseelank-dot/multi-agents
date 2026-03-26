const mongoose = require('mongoose');
const ChatRoom = require('../models/ChatRoom');

describe('ChatRoom Model', () => {
  describe('Schema Validation', () => {
    it('should require name', () => {
      const room = new ChatRoom({});
      const error = room.validateSync();
      expect(error.errors.name).toBeDefined();
      expect(error.errors.name.message).toBe('Chat room name is required');
    });

    it('should reject empty name', () => {
      const room = new ChatRoom({ name: '' });
      const error = room.validateSync();
      expect(error.errors.name).toBeDefined();
    });

    it('should be valid with only required name field', () => {
      const room = new ChatRoom({ name: 'General' });
      const error = room.validateSync();
      expect(error).toBeUndefined();
    });

    it('should be valid with all fields provided', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();
      const room = new ChatRoom({
        name: 'Dev Team',
        description: 'Development team chat',
        type: 'private',
        participants: [user1, user2],
        admin: [user1],
        isActive: true,
      });
      const error = room.validateSync();
      expect(error).toBeUndefined();
    });

    it('should reject name exceeding 50 characters', () => {
      const room = new ChatRoom({ name: 'a'.repeat(51) });
      const error = room.validateSync();
      expect(error.errors.name).toBeDefined();
      expect(error.errors.name.message).toBe('Room name cannot exceed 50 characters');
    });

    it('should accept name at exactly 50 characters', () => {
      const room = new ChatRoom({ name: 'a'.repeat(50) });
      const error = room.validateSync();
      expect(error).toBeUndefined();
    });

    it('should reject description exceeding 200 characters', () => {
      const room = new ChatRoom({
        name: 'General',
        description: 'a'.repeat(201),
      });
      const error = room.validateSync();
      expect(error.errors.description).toBeDefined();
      expect(error.errors.description.message).toBe(
        'Description cannot exceed 200 characters'
      );
    });

    it('should accept description at exactly 200 characters', () => {
      const room = new ChatRoom({
        name: 'General',
        description: 'a'.repeat(200),
      });
      const error = room.validateSync();
      expect(error).toBeUndefined();
    });

    it('should trim whitespace from name', () => {
      const room = new ChatRoom({ name: '  General  ' });
      expect(room.name).toBe('General');
    });

    it('should trim whitespace from description', () => {
      const room = new ChatRoom({
        name: 'General',
        description: '  A chat room  ',
      });
      expect(room.description).toBe('A chat room');
    });
  });

  describe('Type Enum', () => {
    it('should accept public type', () => {
      const room = new ChatRoom({ name: 'General', type: 'public' });
      expect(room.type).toBe('public');
    });

    it('should accept private type', () => {
      const room = new ChatRoom({ name: 'Private Room', type: 'private' });
      expect(room.type).toBe('private');
    });

    it('should accept direct type', () => {
      const room = new ChatRoom({ name: 'Direct', type: 'direct' });
      expect(room.type).toBe('direct');
    });

    it('should default to public type', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.type).toBe('public');
    });

    it('should reject invalid type', () => {
      const room = new ChatRoom({ name: 'General', type: 'channel' });
      const error = room.validateSync();
      expect(error.errors.type).toBeDefined();
    });

    it('should reject type with arbitrary value', () => {
      const room = new ChatRoom({ name: 'General', type: 'random' });
      const error = room.validateSync();
      expect(error.errors.type).toBeDefined();
    });
  });

  describe('Default Values', () => {
    it('should set description to empty string by default', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.description).toBe('');
    });

    it('should set isActive to true by default', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.isActive).toBe(true);
    });

    it('should have empty participants array by default', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.participants).toEqual([]);
    });

    it('should have empty admin array by default', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.admin).toEqual([]);
    });

    it('should set lastMessage to undefined by default', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.lastMessage).toBeUndefined();
    });
  });

  describe('Participants', () => {
    it('should accept participants as ObjectId array', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();
      const room = new ChatRoom({
        name: 'General',
        participants: [user1, user2],
      });
      expect(room.participants).toHaveLength(2);
      expect(room.participants[0]).toEqual(user1);
      expect(room.participants[1]).toEqual(user2);
    });

    it('should reference User model in participants', () => {
      const participantsPath = ChatRoom.schema.path('participants');
      const caster = participantsPath.caster;
      expect(caster.options.ref).toBe('User');
    });

    it('should store ObjectId in participants', () => {
      const participantsPath = ChatRoom.schema.path('participants');
      const caster = participantsPath.caster;
      expect(caster.instance).toBe('ObjectId');
    });

    it('should allow adding participants dynamically', () => {
      const room = new ChatRoom({ name: 'General' });
      const userId = new mongoose.Types.ObjectId();
      room.participants.push(userId);
      expect(room.participants).toHaveLength(1);
      expect(room.participants[0]).toEqual(userId);
    });
  });

  describe('Admin', () => {
    it('should accept admin as ObjectId array', () => {
      const adminId = new mongoose.Types.ObjectId();
      const room = new ChatRoom({
        name: 'General',
        admin: [adminId],
      });
      expect(room.admin).toHaveLength(1);
      expect(room.admin[0]).toEqual(adminId);
    });

    it('should reference User model in admin', () => {
      const adminPath = ChatRoom.schema.path('admin');
      const caster = adminPath.caster;
      expect(caster.options.ref).toBe('User');
    });

    it('should store ObjectId in admin', () => {
      const adminPath = ChatRoom.schema.path('admin');
      const caster = adminPath.caster;
      expect(caster.instance).toBe('ObjectId');
    });

    it('should allow multiple admins', () => {
      const admin1 = new mongoose.Types.ObjectId();
      const admin2 = new mongoose.Types.ObjectId();
      const room = new ChatRoom({
        name: 'General',
        admin: [admin1, admin2],
      });
      expect(room.admin).toHaveLength(2);
    });
  });

  describe('Last Message Reference', () => {
    it('should reference Message model in lastMessage', () => {
      const lastMessagePath = ChatRoom.schema.path('lastMessage');
      expect(lastMessagePath.options.ref).toBe('Message');
    });

    it('should accept lastMessage as ObjectId', () => {
      const messageId = new mongoose.Types.ObjectId();
      const room = new ChatRoom({
        name: 'General',
        lastMessage: messageId,
      });
      expect(room.lastMessage).toEqual(messageId);
    });
  });

  describe('Timestamps', () => {
    it('should have timestamps enabled', () => {
      expect(ChatRoom.schema.options.timestamps).toBe(true);
    });
  });

  describe('Indexes', () => {
    it('should have text index on name and description', () => {
      const indexes = ChatRoom.schema.indexes();
      const hasTextIndex = indexes.some(
        (idx) => idx[0].name === 'text' && idx[0].description === 'text'
      );
      expect(hasTextIndex).toBe(true);
    });

    it('should have index on participants', () => {
      const indexes = ChatRoom.schema.indexes();
      const hasIndex = indexes.some((idx) => idx[0].participants === 1);
      expect(hasIndex).toBe(true);
    });

    it('should have index on type', () => {
      const indexes = ChatRoom.schema.indexes();
      const hasIndex = indexes.some((idx) => idx[0].type === 1);
      expect(hasIndex).toBe(true);
    });
  });

  describe('isActive Toggle', () => {
    it('should allow setting isActive to false', () => {
      const room = new ChatRoom({
        name: 'Archived Room',
        isActive: false,
      });
      expect(room.isActive).toBe(false);
    });

    it('should allow toggling isActive', () => {
      const room = new ChatRoom({ name: 'General' });
      expect(room.isActive).toBe(true);
      room.isActive = false;
      expect(room.isActive).toBe(false);
      room.isActive = true;
      expect(room.isActive).toBe(true);
    });
  });

  describe('Combined Scenarios', () => {
    it('should create a public room with participants and admin', () => {
      const admin = new mongoose.Types.ObjectId();
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();

      const room = new ChatRoom({
        name: 'Team Chat',
        description: 'Our team channel',
        type: 'public',
        participants: [admin, user1, user2],
        admin: [admin],
      });

      expect(room.name).toBe('Team Chat');
      expect(room.type).toBe('public');
      expect(room.participants).toHaveLength(3);
      expect(room.admin).toHaveLength(1);
      expect(room.isActive).toBe(true);
    });

    it('should create a private direct room', () => {
      const user1 = new mongoose.Types.ObjectId();
      const user2 = new mongoose.Types.ObjectId();

      const room = new ChatRoom({
        name: 'DM',
        type: 'direct',
        participants: [user1, user2],
      });

      expect(room.type).toBe('direct');
      expect(room.participants).toHaveLength(2);
      expect(room.admin).toHaveLength(0);
    });

    it('should create an archived room', () => {
      const room = new ChatRoom({
        name: 'Old Project',
        description: 'Archived project room',
        type: 'private',
        isActive: false,
      });

      expect(room.isActive).toBe(false);
      expect(room.type).toBe('private');
    });
  });
});
