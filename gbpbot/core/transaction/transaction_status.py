from enum import Enum, auto

class TransactionStatus(Enum):
    """
    Enum for tracking the status of blockchain transactions
    """
    PENDING = auto()         # Transaction has been submitted but not confirmed
    CONFIRMING = auto()      # Transaction is being confirmed (has some confirmations)
    CONFIRMED = auto()       # Transaction has been confirmed with enough confirmations
    FAILED = auto()          # Transaction failed to execute
    REJECTED = auto()        # Transaction was rejected by the network
    TIMEOUT = auto()         # Transaction confirmation timed out
    DROPPED = auto()         # Transaction was dropped from the mempool
    REPLACED = auto()        # Transaction was replaced by another transaction
    UNKNOWN = auto()         # Transaction status is unknown

    @classmethod
    def is_final(cls, status):
        """
        Check if a transaction status is considered final (no longer changing)
        
        Args:
            status: TransactionStatus to check
            
        Returns:
            bool: True if the status is final, False otherwise
        """
        return status in [
            cls.CONFIRMED,
            cls.FAILED,
            cls.REJECTED,
            cls.TIMEOUT,
            cls.DROPPED,
            cls.REPLACED
        ]
    
    @classmethod
    def is_successful(cls, status):
        """
        Check if a transaction status is considered successful
        
        Args:
            status: TransactionStatus to check
            
        Returns:
            bool: True if the status is successful, False otherwise
        """
        return status == cls.CONFIRMED
    
    @classmethod
    def from_string(cls, status_str):
        """
        Convert a string to a TransactionStatus
        
        Args:
            status_str: String representation of a transaction status
            
        Returns:
            TransactionStatus: Corresponding transaction status
        """
        status_map = {
            "pending": cls.PENDING,
            "confirming": cls.CONFIRMING,
            "confirmed": cls.CONFIRMED,
            "failed": cls.FAILED,
            "rejected": cls.REJECTED,
            "timeout": cls.TIMEOUT,
            "dropped": cls.DROPPED,
            "replaced": cls.REPLACED,
            "unknown": cls.UNKNOWN
        }
        
        return status_map.get(status_str.lower(), cls.UNKNOWN) 