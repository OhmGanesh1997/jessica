import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import {
  Calendar as CalendarIcon,
  Plus,
  ChevronLeft,
  ChevronRight,
  Clock,
  Users,
  MapPin,
  Video,
  Phone,
  Zap,
  RefreshCw,
  Filter,
  Search,
  Edit,
  Trash2,
  Copy
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

// Calendar API functions
const fetchCalendarEvents = async ({ queryKey }) => {
  const [_key, params] = queryKey;
  const response = await axios.get('/api/calendar/events', { params });
  return response.data;
};

const createCalendarEvent = async (eventData) => {
  const response = await axios.post('/api/calendar/events', eventData);
  return response.data;
};

const updateCalendarEvent = async ({ id, data }) => {
  const response = await axios.put(`/api/calendar/events/${id}`, data);
  return response.data;
};

const deleteCalendarEvent = async (id) => {
  const response = await axios.delete(`/api/calendar/events/${id}`);
  return response.data;
};

const findOptimalTime = async (requirements) => {
  const response = await axios.post('/api/ai/find-optimal-time', requirements);
  return response.data;
};

const syncCalendars = async () => {
  const response = await axios.post('/api/calendar/sync');
  return response.data;
};

// Calendar View Component
const CalendarView = ({ currentDate, setCurrentDate, events, onEventClick }) => {
  const getDaysInMonth = (date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const getEventsForDate = (date) => {
    return events?.filter(event => {
      const eventDate = new Date(event.start_datetime);
      return eventDate.toDateString() === date.toDateString();
    }) || [];
  };

  const renderCalendarDay = (dayNumber, monthDate) => {
    const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), dayNumber);
    const dayEvents = getEventsForDate(date);
    const isCurrentDay = isToday(date);

    return (
      <div
        key={dayNumber}
        className={`
          min-h-[100px] p-2 border border-gray-100 cursor-pointer transition-colors
          ${isCurrentDay ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'}
        `}
        onClick={() => onEventClick(null, date)}
      >
        <div className={`
          text-sm font-medium mb-1
          ${isCurrentDay ? 'text-blue-600' : 'text-gray-900'}
        `}>
          {dayNumber}
        </div>
        <div className="space-y-1">
          {dayEvents.slice(0, 3).map((event, index) => (
            <div
              key={event.id}
              onClick={(e) => {
                e.stopPropagation();
                onEventClick(event);
              }}
              className={`
                text-xs p-1 rounded truncate cursor-pointer transition-colors
                ${event.ai_analysis?.optimal_time_score > 0.7 
                  ? 'bg-green-100 text-green-800 hover:bg-green-200' 
                  : event.ai_analysis?.optimal_time_score > 0.4
                  ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                  : 'bg-red-100 text-red-800 hover:bg-red-200'
                }
              `}
              title={event.title}
            >
              {new Date(event.start_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {event.title}
            </div>
          ))}
          {dayEvents.length > 3 && (
            <div className="text-xs text-gray-500">
              +{dayEvents.length - 3} more
            </div>
          )}
        </div>
      </div>
    );
  };

  const daysInMonth = getDaysInMonth(currentDate);
  const firstDay = getFirstDayOfMonth(currentDate);
  const daysArray = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const emptyDays = Array.from({ length: firstDay }, (_, i) => i);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Calendar Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="text-xl font-semibold text-gray-900">
            {currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </h2>
          <button
            onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
        <button
          onClick={() => setCurrentDate(new Date())}
          className="btn btn-outline btn-sm"
        >
          Today
        </button>
      </div>

      {/* Weekday Headers */}
      <div className="grid grid-cols-7 border-b border-gray-200">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <div key={day} className="p-3 text-center text-sm font-medium text-gray-600 border-r border-gray-100 last:border-r-0">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7">
        {/* Empty days */}
        {emptyDays.map((_, index) => (
          <div key={`empty-${index}`} className="min-h-[100px] p-2 border border-gray-100 bg-gray-50"></div>
        ))}
        
        {/* Days with events */}
        {daysArray.map((day) => renderCalendarDay(day, currentDate))}
      </div>
    </div>
  );
};

// Event Detail Modal
const EventDetailModal = ({ event, isOpen, onClose, onEdit, onDelete }) => {
  if (!isOpen || !event) return null;

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this event?')) {
      onDelete(event.id);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{event.title}</h2>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>
                    {new Date(event.start_datetime).toLocaleString()} - 
                    {new Date(event.end_datetime).toLocaleString()}
                  </span>
                </div>
                {event.attendees?.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <Users className="w-4 h-4" />
                    <span>{event.attendees.length} attendees</span>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-6">
          {event.description && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-900 mb-2">Description</h3>
              <p className="text-gray-700">{event.description}</p>
            </div>
          )}

          {event.location && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-900 mb-2">Location</h3>
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-gray-400" />
                <span className="text-gray-700">{event.location.name}</span>
              </div>
            </div>
          )}

          {event.attendees?.length > 0 && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-900 mb-2">Attendees</h3>
              <div className="space-y-2">
                {event.attendees.map((attendee, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <div className="w-6 h-6 bg-gray-300 rounded-full flex items-center justify-center">
                      <span className="text-xs">{attendee.email?.[0]?.toUpperCase()}</span>
                    </div>
                    <span className="text-gray-700">{attendee.name || attendee.email}</span>
                    <span className="text-xs text-gray-500">({attendee.response_status || 'pending'})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Analysis */}
          {event.ai_analysis && (
            <div className="mb-6 bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-3">
                <Zap className="w-4 h-4 text-blue-600" />
                <h3 className="font-medium text-gray-900">AI Optimization Analysis</h3>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Optimal Time Score:</span>
                  <div className="mt-1">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          event.ai_analysis.optimal_time_score > 0.7 ? 'bg-green-500' :
                          event.ai_analysis.optimal_time_score > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${event.ai_analysis.optimal_time_score * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-gray-500">
                      {Math.round(event.ai_analysis.optimal_time_score * 100)}%
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Productivity Impact:</span>
                  <span className="ml-2 font-medium capitalize">{event.ai_analysis.productivity_impact}</span>
                </div>
                <div>
                  <span className="text-gray-600">Meeting Type:</span>
                  <span className="ml-2 font-medium capitalize">{event.ai_analysis.meeting_type_classification}</span>
                </div>
                <div>
                  <span className="text-gray-600">Prep Time Needed:</span>
                  <span className="ml-2 font-medium">{event.ai_analysis.estimated_preparation_time} mins</span>
                </div>
              </div>
              
              {event.ai_analysis.scheduling_suggestions?.length > 0 && (
                <div className="mt-3">
                  <span className="text-gray-600 text-sm">AI Suggestions:</span>
                  <ul className="mt-1 space-y-1">
                    {event.ai_analysis.scheduling_suggestions.map((suggestion, index) => (
                      <li key={index} className="text-sm text-gray-700">• {suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-200 flex items-center justify-between">
          <div className="flex space-x-3">
            <button
              onClick={() => onEdit(event)}
              className="btn btn-outline"
            >
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </button>
            <button
              onClick={() => navigator.clipboard.writeText(event.id)}
              className="btn btn-outline"
            >
              <Copy className="w-4 h-4 mr-2" />
              Copy Link
            </button>
          </div>
          <button
            onClick={handleDelete}
            className="btn btn-outline text-red-600 hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </button>
        </div>
      </motion.div>
    </div>
  );
};

const CalendarPage = () => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showEventModal, setShowEventModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);

  const queryClient = useQueryClient();

  // Fetch calendar events
  const { data: eventsData, isLoading, error } = useQuery(
    ['calendarEvents', { 
      month: currentDate.getMonth() + 1,
      year: currentDate.getFullYear()
    }],
    fetchCalendarEvents,
    {
      refetchInterval: 60000, // Refetch every minute
    }
  );

  // Sync calendars mutation
  const syncMutation = useMutation(syncCalendars, {
    onSuccess: () => {
      queryClient.invalidateQueries('calendarEvents');
      toast.success('Calendars synced successfully!');
    },
    onError: () => {
      toast.error('Failed to sync calendars');
    }
  });

  // Delete event mutation
  const deleteMutation = useMutation(deleteCalendarEvent, {
    onSuccess: () => {
      queryClient.invalidateQueries('calendarEvents');
      toast.success('Event deleted successfully!');
    },
    onError: () => {
      toast.error('Failed to delete event');
    }
  });

  // Find optimal time mutation
  const optimalTimeMutation = useMutation(findOptimalTime, {
    onSuccess: (data) => {
      toast.success('AI found optimal meeting times!');
      // Show results in a modal or redirect to scheduling interface
    },
    onError: () => {
      toast.error('Failed to find optimal times');
    }
  });

  const handleEventClick = (event, date = null) => {
    if (event) {
      setSelectedEvent(event);
      setShowEventModal(true);
    } else {
      setSelectedDate(date);
      setShowCreateModal(true);
    }
  };

  const handleSync = () => {
    syncMutation.mutate();
  };

  const handleFindOptimalTime = () => {
    // This would open a modal to input requirements
    const requirements = {
      title: "New Meeting",
      duration_minutes: 60,
      attendee_emails: [],
      preferred_times: ["10:00", "14:00"],
      date_range_start: new Date().toISOString(),
      date_range_end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
    };
    optimalTimeMutation.mutate(requirements);
  };

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load calendar events. Please try again.</p>
        <button onClick={() => queryClient.invalidateQueries('calendarEvents')} className="btn btn-primary mt-4">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Smart Calendar</h1>
          <p className="text-gray-600">AI-powered scheduling and calendar optimization</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleFindOptimalTime}
            disabled={optimalTimeMutation.isLoading}
            className="btn btn-outline"
          >
            {optimalTimeMutation.isLoading ? (
              <div className="animate-spin w-4 h-4 border-2 border-blue-600/30 border-t-blue-600 rounded-full mr-2"></div>
            ) : (
              <Zap className="w-4 h-4 mr-2" />
            )}
            Find Optimal Time
          </button>
          <button
            onClick={handleSync}
            disabled={syncMutation.isLoading}
            className="btn btn-outline"
          >
            {syncMutation.isLoading ? (
              <div className="animate-spin w-4 h-4 border-2 border-gray-600/30 border-t-gray-600 rounded-full mr-2"></div>
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Sync Calendars
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Event
          </button>
        </div>
      </div>

      {/* AI Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6"
      >
        <div className="flex items-center space-x-3 mb-4">
          <Zap className="w-6 h-6 text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-900">AI Calendar Insights</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="text-2xl font-bold text-blue-600 mb-1">85%</div>
            <div className="text-sm text-gray-600">Optimal scheduling score this week</div>
          </div>
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="text-2xl font-bold text-green-600 mb-1">2.5h</div>
            <div className="text-sm text-gray-600">Average prep time saved with AI scheduling</div>
          </div>
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="text-2xl font-bold text-orange-600 mb-1">3</div>
            <div className="text-sm text-gray-600">Conflicts detected and resolved automatically</div>
          </div>
        </div>
      </motion.div>

      {/* Calendar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {isLoading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8">
            <div className="animate-pulse space-y-4">
              <div className="h-8 bg-gray-200 rounded w-1/4"></div>
              <div className="grid grid-cols-7 gap-4">
                {[...Array(35)].map((_, i) => (
                  <div key={i} className="h-24 bg-gray-100 rounded"></div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <CalendarView
            currentDate={currentDate}
            setCurrentDate={setCurrentDate}
            events={eventsData?.events || []}
            onEventClick={handleEventClick}
          />
        )}
      </motion.div>

      {/* Event Detail Modal */}
      <EventDetailModal
        event={selectedEvent}
        isOpen={showEventModal}
        onClose={() => {
          setShowEventModal(false);
          setSelectedEvent(null);
        }}
        onEdit={(event) => {
          // Handle edit event
          console.log('Edit event:', event);
        }}
        onDelete={deleteMutation.mutate}
      />
    </div>
  );
};

export default CalendarPage;