import uuid
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET
from app.core.database import Base


class ContainerService(Base):
    """
    Maps each exposed service in a lab to its own VPN IP and optional hostname.
    A single container (lab deployment) can have multiple services.
    """
    __tablename__ = "container_services"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_name = Column(
        String,
        nullable=False,
        doc="Docker Compose service name",
    )
    hostname = Column(
        String,
        nullable=True,
        doc="Optional DNS hostname (e.g. 'web.lab', 'db.lab')",
    )
    vpn_ip = Column(
        INET,
        nullable=False,
        doc="VPN IP assigned to this service",
    )
    vpn_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vpn_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )
