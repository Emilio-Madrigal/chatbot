import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database module before importing menu_system
sys.modules['database.database'] = MagicMock()
sys.modules['database.models'] = MagicMock()

from services.menu_system import MenuSystem

class TestMenuSystem(unittest.TestCase):
    def setUp(self):
        self.menu = MenuSystem()
        # Mock services
        self.menu.actions_service = MagicMock()
        self.menu.citas_service = MagicMock()
        self.menu.firebase_service = MagicMock()
        self.menu.db = MagicMock()
        
        # Setup common mock returns
        self.menu.actions_service.get_consultorios_info.return_value = [
            {'id': 'cons1', 'nombre': 'Consultorio Central', 'direccion': 'Calle 123'}
        ]
        
        # Mock repository for dates/times
        self.cita_repo_mock = MagicMock()
        self.cita_repo_mock.obtener_fechas_disponibles.return_value = [
            datetime(2025, 1, 24), datetime(2025, 1, 25)
        ]
        self.cita_repo_mock.obtener_horarios_disponibles.return_value = [
            {'horaInicio': '10:00', 'horaFin': '10:30'}
        ]
        
        # Patch the local import of CitaRepository in menu_system methods
        self.modules_patcher = patch.dict(sys.modules, {'database.models': MagicMock()})
        self.modules_patcher.start()
        sys.modules['database.models'].CitaRepository.return_value = self.cita_repo_mock

    def tearDown(self):
        self.modules_patcher.stop()

    def test_01_schedule_appointment_flow(self):
        print("\n--- Testing Option 1: Schedule Appointment ---")
        session_id = "test_session"
        context = {}
        
        # 1. Main Menu -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_consultorio')
        self.assertIn('Selecciona un consultorio', response['response'])
        
        # 2. Select Consultorio -> Select 1
        # Mock dentistas query
        mock_stream = MagicMock()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {'dentistaId': 'dent1', 'nombreCompleto': 'Dr. Test', 'especialidad': 'General'}
        mock_doc.id = 'dent1'
        mock_stream.stream.return_value = [mock_doc] # This returns an iterator
        # We need properly mock the chain: db.collection().document().collection().where().limit().stream()
        self.menu.db.collection.return_value.document.return_value.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_dentista')
        self.assertIn('Dr. Test', response['response'])
        
        # 3. Select Dentista -> Select 1
        # Mock services
        self.menu.actions_service.get_treatments_for_dentist.return_value = [
            {'id': 't1', 'nombre': 'Limpieza', 'precio': 500, 'duracion': 30}
        ]
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_servicio')
        self.assertIn('Limpieza', response['response'])
        
        # 4. Select Service -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_fecha_agendar')
        self.assertIn('Selecciona una fecha', response['response'])
        
        # 5. Select Date -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_hora_agendar')
        self.assertIn('10:00', response['response'])
        
        # 6. Select Time -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_metodo_pago')
        
        # 7. Select Payment -> Select 1 (Cash)
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_historial_medico')
        
        # 8. Select Medical History -> Select 1 (No share)
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'mostrando_resumen')
        self.assertIn('Resumen de tu Cita', response['response'])
        
        # 9. Confirm -> Select 1
        self.menu.firebase_service.create_appointment.return_value = {'success': True}
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'menu_principal')
        self.assertIn('Cita Agendada Exitosamente', response['response'])
        print("Option 1 Flow: SUCCESS")

    def test_03_reschedule_appointment_flow(self):
        print("\n--- Testing Option 3: Reschedule Appointment ---")
        session_id = "test_session"
        context = {}
        
        # Mock user appointments
        self.menu.firebase_service.get_user_appointments.return_value = [
            {'id': 'cita1', 'fecha': '2025-01-20', 'hora': '09:00', 'dentista': 'Dr. Test', 
             'dentistaId': 'dent1', 'consultorioId': 'cons1'}
        ]
        
        # 1. Main Menu -> Select 3
        response = self.menu.process_message(session_id, "3", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_cita_reagendar')
        
        # 2. Select Cita -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_fecha_reagendar')
        
        # 3. Select Date -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_hora_reagendar')
        
        # 4. Select Time -> Select 1
        # This was the broken step - should now show confirmation
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'confirmando_reagendamiento')
        self.assertIn('Confirmar Reagendamiento', response['response'])
        
        # 5. Confirm -> Select 1
        self.menu.firebase_service.reschedule_appointment.return_value = {'success': True}
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'menu_principal')
        self.assertIn('Cita Reagendada Exitosamente', response['response'])
        print("Option 3 Flow: SUCCESS")

    def test_04_cancel_appointment_flow(self):
        print("\n--- Testing Option 4: Cancel Appointment ---")
        session_id = "test_session"
        context = {}
        
        # Mock user appointments
        self.menu.firebase_service.get_user_appointments.return_value = [
            {'id': 'cita1', 'fecha': '2025-01-20', 'hora': '09:00', 'dentista': 'Dr. Test'}
        ]
        
        # 1. Main Menu -> Select 4
        response = self.menu.process_message(session_id, "4", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'seleccionando_cita_cancelar')
        
        # 2. Select Cita -> Select 1
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'confirmando_cancelacion')
        
        # 3. Confirm -> Select 1
        self.menu.firebase_service.cancel_appointment.return_value = {'success': True}
        response = self.menu.process_message(session_id, "1", context, "user1", "5551234567")
        self.assertEqual(context['step'], 'menu_principal')
        self.assertIn('Cita Cancelada Exitosamente', response['response'])
        print("Option 4 Flow: SUCCESS")

if __name__ == '__main__':
    unittest.main()
