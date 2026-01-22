# Idaho Retailer - Customer Zones and Response Times

## Customer Zones (L = 6):

1. **Boise Metro Zone** - Downtown Boise, Boise bench areas
   - Closest to: Boise Downtown Store, Boise Urban FC

2. **West Treasure Valley Zone** - Meridian, Nampa, Caldwell
   - Closest to: Boise Urban FC, Boise Downtown Store

3. **Idaho Falls Metro Zone** - Idaho Falls city and immediate suburbs
   - Closest to: Idaho Falls Store, Pocatello FC

4. **Southeast Idaho Zone** - Pocatello, Blackfoot, Rexburg
   - Closest to: Pocatello FC, Idaho Falls Store

5. **Coeur d'Alene Metro Zone** - Coeur d'Alene, Post Falls, Hayden
   - Closest to: Coeur d'Alene Store

6. **North Idaho Rural Zone** - Sandpoint, Moscow, Lewiston
   - Closest to: Coeur d'Alene Store

---

## Supply Points:

### Existing Stores (S = 3):
- **s1**: Boise Downtown Store
- **s2**: Idaho Falls Store
- **s3**: Coeur d'Alene Store

### Potential Fulfillment Centers (F = 2):
- **f1**: Boise Urban FC
- **f2**: Pocatello FC

### Warehouse:
- **w**: Central Warehouse (Boise) - Always operational

---

## Response Time Matrix (days from each supply point to each zone):

| Supply Point | Boise Metro (l1) | West TV (l2) | IF Metro (l3) | SE Idaho (l4) | CDA Metro (l5) | North Rural (l6) |
|--------------|------------------|--------------|---------------|---------------|----------------|------------------|
| Boise Store (s1) | 1 | 1 | 2 | 2 | 2 | 2 |
| Idaho Falls Store (s2) | 2 | 2 | 1 | 1 | 2 | 2 |
| Coeur d'Alene Store (s3) | 2 | 2 | 2 | 2 | 1 | 1 |
| Boise Urban FC (f1) | 1 | 1 | 2 | 2 | 2 | 2 |
| Pocatello FC (f2) | 1 | 1 | 1 | 1 | 2 | 2 |
| Central Warehouse (w) | 2 | 2 | 2 | 2 | 2 | 2 |

---

## Geographic Coverage Notes:

- **Boise Metro + West TV**: Core Treasure Valley market (highest population density)
- **IF Metro + SE Idaho**: Eastern Idaho corridor
- **CDA Metro + North Rural**: Northern Idaho region
- **Warehouse**: Centralized in Boise, 2-day minimum to all zones
- **FC Strategy**: 
  - Boise Urban FC enables 1-day delivery to western zones
  - Pocatello FC enables 1-day delivery to eastern zones (including Boise via proximity)
