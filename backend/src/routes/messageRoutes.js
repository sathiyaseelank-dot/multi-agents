const express = require('express');
const { body, validationResult } = require('express-validator');
const Message = require('../models/Message');
const Conversation = require('../models/Conversation');
const { protect } = require('../middleware/auth');

const router = express.Router();

router.get('/conversation/:conversationId', protect, async (req, res) => {
  try {
    const { page = 1, limit = 50 } = req.query;

    const conversation = await Conversation.findById(
      req.params.conversationId
    );
    if (!conversation) {
      return res.status(404).json({
        success: false,
        error: 'Conversation not found',
      });
    }

    if (!conversation.isParticipant(req.user.id)) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized to view these messages',
      });
    }

    const messages = await Message.find({
      conversationId: req.params.conversationId,
      isDeleted: false,
    })
      .populate('sender', 'username avatar')
      .populate('replyTo')
      .sort({ createdAt: -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));

    const total = await Message.countDocuments({
      conversationId: req.params.conversationId,
      isDeleted: false,
    });

    res.json({
      success: true,
      data: messages.reverse(),
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

router.post(
  '/',
  protect,
  [
    body('conversationId')
      .notEmpty()
      .withMessage('Conversation ID is required'),
    body('content')
      .if((value, { req }) => !req.body.messageType || req.body.messageType === 'text')
      .notEmpty()
      .withMessage('Message content is required for text messages'),
  ],
  async (req, res) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({
          success: false,
          error: errors.array().map((e) => e.msg).join(', '),
        });
      }

      const { conversationId, content, messageType = 'text', mediaUrl, replyTo } =
        req.body;

      const conversation = await Conversation.findById(conversationId);
      if (!conversation) {
        return res.status(404).json({
          success: false,
          error: 'Conversation not found',
        });
      }

      if (!conversation.isParticipant(req.user.id)) {
        return res.status(403).json({
          success: false,
          error: 'Not authorized to send messages to this conversation',
        });
      }

      const message = await Message.create({
        conversationId,
        sender: req.user.id,
        content,
        messageType,
        mediaUrl,
        replyTo,
        readBy: [{ user: req.user.id }],
      });

      conversation.lastMessage = message._id;
      conversation.lastMessageAt = new Date();

      const senderUnread = conversation.unreadCount.find(
        (u) => u.user.toString() === req.user.id
      );
      if (senderUnread) {
        senderUnread.count = 0;
      }

      await conversation.save();

      const populatedMessage = await Message.findById(message._id).populate(
        'sender',
        'username avatar'
      );

      req.app.get('io').to(conversationId).emit('newMessage', populatedMessage);

      res.status(201).json({
        success: true,
        data: populatedMessage,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }
);

router.put('/:id/read', protect, async (req, res) => {
  try {
    const message = await Message.findById(req.params.id);
    if (!message) {
      return res.status(404).json({
        success: false,
        error: 'Message not found',
      });
    }

    const conversation = await Conversation.findById(message.conversationId);
    if (!conversation.isParticipant(req.user.id)) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized',
      });
    }

    if (!message.isReadBy(req.user.id)) {
      message.readBy.push({ user: req.user.id });
      await message.save();

      const participantUnread = conversation.unreadCount.find(
        (u) => u.user.toString() === req.user.id
      );
      if (participantUnread && participantUnread.count > 0) {
        participantUnread.count -= 1;
        await conversation.save();
      }
    }

    res.json({
      success: true,
      data: message,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

router.put('/:id/reaction', protect, async (req, res) => {
  try {
    const { emoji, action } = req.body;
    const message = await Message.findById(req.params.id);

    if (!message) {
      return res.status(404).json({
        success: false,
        error: 'Message not found',
      });
    }

    if (action === 'remove') {
      message.removeReaction(req.user.id, emoji);
    } else {
      message.addReaction(req.user.id, emoji);
    }

    await message.save();

    res.json({
      success: true,
      data: message,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

router.delete('/:id', protect, async (req, res) => {
  try {
    const message = await Message.findById(req.params.id);
    if (!message) {
      return res.status(404).json({
        success: false,
        error: 'Message not found',
      });
    }

    if (message.sender.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized to delete this message',
      });
    }

    message.isDeleted = true;
    message.deletedAt = new Date();
    message.content = 'This message was deleted';
    await message.save();

    res.json({
      success: true,
      message: 'Message deleted successfully',
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

module.exports = router;
