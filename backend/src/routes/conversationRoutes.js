const express = require('express');
const { body, validationResult } = require('express-validator');
const Conversation = require('../models/Conversation');
const User = require('../models/User');
const { protect } = require('../middleware/auth');

const router = express.Router();

router.get('/', protect, async (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;

    const conversations = await Conversation.find({
      'participants.user': req.user.id,
      isActive: true,
    })
      .populate('participants.user', 'username email avatar status lastSeen')
      .populate('lastMessage')
      .sort({ lastMessageAt: -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));

    res.json({
      success: true,
      data: conversations,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

router.get('/:id', protect, async (req, res) => {
  try {
    const conversation = await Conversation.findById(req.params.id)
      .populate('participants.user', 'username email avatar status lastSeen')
      .populate('lastMessage');

    if (!conversation) {
      return res.status(404).json({
        success: false,
        error: 'Conversation not found',
      });
    }

    if (!conversation.isParticipant(req.user.id)) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized to view this conversation',
      });
    }

    res.json({
      success: true,
      data: conversation,
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
    body('participantId')
      .notEmpty()
      .withMessage('Participant ID is required for direct messages'),
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

      const { participantId, type = 'direct', name, description } = req.body;

      const participant = await User.findById(participantId);
      if (!participant) {
        return res.status(404).json({
          success: false,
          error: 'Participant not found',
        });
      }

      if (type === 'direct') {
        const existingConversation = await Conversation.findOne({
          type: 'direct',
          participants: {
            $all: [
              { $elemMatch: { user: req.user.id } },
              { $elemMatch: { user: participantId } },
            ],
          },
        });

        if (existingConversation) {
          return res.json({
            success: true,
            data: existingConversation,
            isExisting: true,
          });
        }
      }

      const conversation = await Conversation.create({
        type,
        name: type === 'group' ? name : undefined,
        description: type === 'group' ? description : undefined,
        participants: [
          { user: req.user.id, role: 'admin' },
          { user: participantId, role: 'member' },
        ],
        unreadCount: [
          { user: req.user.id, count: 0 },
          { user: participantId, count: 0 },
        ],
      });

      await User.findByIdAndUpdate(req.user.id, {
        $push: { conversations: conversation._id },
      });
      await User.findByIdAndUpdate(participantId, {
        $push: { conversations: conversation._id },
      });

      const populatedConversation = await Conversation.findById(
        conversation._id
      ).populate('participants.user', 'username email avatar status lastSeen');

      res.status(201).json({
        success: true,
        data: populatedConversation,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }
);

router.put('/:id', protect, async (req, res) => {
  try {
    const conversation = await Conversation.findById(req.params.id);

    if (!conversation) {
      return res.status(404).json({
        success: false,
        error: 'Conversation not found',
      });
    }

    if (!conversation.isParticipant(req.user.id)) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized to update this conversation',
      });
    }

    const { name, description } = req.body;
    if (name) conversation.name = name;
    if (description !== undefined) conversation.description = description;

    await conversation.save();

    res.json({
      success: true,
      data: conversation,
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
    const conversation = await Conversation.findById(req.params.id);

    if (!conversation) {
      return res.status(404).json({
        success: false,
        error: 'Conversation not found',
      });
    }

    if (!conversation.isParticipant(req.user.id)) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized to delete this conversation',
      });
    }

    conversation.isActive = false;
    await conversation.save();

    res.json({
      success: true,
      message: 'Conversation archived successfully',
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

module.exports = router;
