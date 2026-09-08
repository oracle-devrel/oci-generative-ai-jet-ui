package dev.victormartin.agentmemory.chatserver.tools;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

import dev.victormartin.agentmemory.chatserver.model.CustomerOrder;
import dev.victormartin.agentmemory.chatserver.model.OrderStatus;
import dev.victormartin.agentmemory.chatserver.model.SupportTicket;
import dev.victormartin.agentmemory.chatserver.repository.OrderRepository;
import dev.victormartin.agentmemory.chatserver.repository.SupportTicketRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class AgentTools {

    private static final Logger log = LoggerFactory.getLogger(AgentTools.class);
    private static final int RETURN_WINDOW_DAYS = 30;

    private final OrderRepository orderRepository;
    private final SupportTicketRepository supportTicketRepository;
    private final JdbcTemplate jdbcTemplate;

    public AgentTools(OrderRepository orderRepository, SupportTicketRepository supportTicketRepository,
                      JdbcTemplate jdbcTemplate) {
        this.orderRepository = orderRepository;
        this.supportTicketRepository = supportTicketRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    @Tool(description = "Get the current date and time from the database. " +
            "Use this whenever you need to know today's date, for example to check return window eligibility.")
    public String getCurrentDateTime() {
        log.info("[PROCEDURAL] fetching current date/time from database");
        String result = jdbcTemplate.queryForObject("SELECT TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS TZR') FROM DUAL", String.class);
        return "Current date/time: %s".formatted(result);
    }

    @Tool(description = "List all customer orders. Returns a summary of every order including order ID, product, status, and purchase date.")
    public String listOrders() {
        log.info("[PROCEDURAL] listing all orders");
        List<CustomerOrder> orders = orderRepository.findAll();
        if (orders.isEmpty()) {
            return "No orders found.";
        }
        StringBuilder sb = new StringBuilder("Orders:\n");
        for (CustomerOrder o : orders) {
            sb.append("- %s: %s | Qty: %d | $%s | Status: %s | Purchased: %s\n"
                    .formatted(o.getOrderId(), o.getProductName(), o.getQuantity(),
                            o.getTotalAmount(), o.getStatus(), o.getPurchaseDate()));
        }
        return sb.toString();
    }

    @Tool(description = "Look up the status of a customer order by its order ID. " +
            "Returns the current status including shipping information.")
    public String lookupOrderStatus(
            @ToolParam(description = "The order ID to look up, e.g. ORD-1001") String orderId) {
        log.info("[PROCEDURAL] looking up order status for {}", orderId);
        Optional<CustomerOrder> opt = orderRepository.findByOrderId(orderId);
        if (opt.isEmpty()) {
            return "Order %s not found.".formatted(orderId);
        }
        CustomerOrder o = opt.get();
        return "Order %s: %s | Qty: %d | $%s | Status: %s | Purchased: %s | Ship to: %s"
                .formatted(o.getOrderId(), o.getProductName(), o.getQuantity(),
                        o.getTotalAmount(), o.getStatus(), o.getPurchaseDate(), o.getShippingAddress());
    }

    @Tool(description = "Initiate a product return for a given order. " +
            "Validates the order exists, checks that it is in DELIVERED status, " +
            "and verifies the return is within the 30-day return window. " +
            "Use this when a customer wants to return a product.")
    public String initiateReturn(
            @ToolParam(description = "The order ID to return") String orderId,
            @ToolParam(description = "The reason for the return") String reason) {
        log.info("[PROCEDURAL] initiating return for order {} reason: {}", orderId, reason);
        Optional<CustomerOrder> opt = orderRepository.findByOrderId(orderId);
        if (opt.isEmpty()) {
            return "Order %s not found. Cannot initiate return.".formatted(orderId);
        }
        CustomerOrder order = opt.get();

        if (order.getStatus() != OrderStatus.DELIVERED) {
            return "Order %s cannot be returned. Current status is %s — only DELIVERED orders are eligible for return."
                    .formatted(orderId, order.getStatus());
        }

        long daysSincePurchase = ChronoUnit.DAYS.between(order.getPurchaseDate(), LocalDate.now());
        if (daysSincePurchase > RETURN_WINDOW_DAYS) {
            return "Order %s cannot be returned. It was purchased %d days ago, which exceeds the %d-day return window."
                    .formatted(orderId, daysSincePurchase, RETURN_WINDOW_DAYS);
        }

        order.setStatus(OrderStatus.PREPARING_RETURN);
        orderRepository.save(order);

        return """
                Return initiated for order %s (%s).
                Reason: %s
                Status changed to PREPARING_RETURN.
                A return label has been generated: RET-%s-001.
                Please ship the item back using the return label. Refund will be processed within 5-7 business days after receipt."""
                .formatted(orderId, order.getProductName(), reason, orderId);
    }

    @Tool(description = "Escalate an issue to a human support agent. Creates a support ticket in the system. " +
            "Use this when the question is beyond your capabilities or the customer explicitly asks for a human.")
    public String escalateToSupport(
            @ToolParam(description = "Brief description of the issue") String issue,
            @ToolParam(description = "Priority level: low, medium, or high") String priority,
            @ToolParam(description = "The related order ID, if applicable. Use null or empty if not related to an order.") String orderId) {
        log.info("[PROCEDURAL] escalating to support — issue: {}, priority: {}, orderId: {}", issue, priority, orderId);

        String normalizedOrderId = (orderId == null || orderId.isBlank()) ? null : orderId;
        SupportTicket ticket = new SupportTicket(normalizedOrderId, issue, priority.toUpperCase());
        supportTicketRepository.save(ticket);

        String eta = switch (priority.toLowerCase()) {
            case "high" -> "1 hour";
            case "medium" -> "4 hours";
            default -> "24 hours";
        };

        return "Support ticket created: SUP-%d. Priority: %s. A human agent will follow up within %s."
                .formatted(ticket.getTicketId(), priority.toUpperCase(), eta);
    }

    @Tool(description = "List all support tickets. Returns ticket ID, related order ID, issue, priority, status, and creation date.")
    public String listSupportTickets() {
        log.info("[PROCEDURAL] listing all support tickets");
        List<SupportTicket> tickets = supportTicketRepository.findAll();
        if (tickets.isEmpty()) {
            return "No support tickets found.";
        }
        StringBuilder sb = new StringBuilder("Support Tickets:\n");
        for (SupportTicket t : tickets) {
            sb.append("- SUP-%d | Order: %s | Issue: %s | Priority: %s | Status: %s | Created: %s\n"
                    .formatted(t.getTicketId(),
                            t.getOrderId() != null ? t.getOrderId() : "N/A",
                            t.getIssue(), t.getPriority(), t.getStatus(), t.getCreatedAt()));
        }
        return sb.toString();
    }
}
